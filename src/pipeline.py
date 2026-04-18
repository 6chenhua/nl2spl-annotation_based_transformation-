"""主Pipeline

协调整个NL到SPL的转换流程。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, cast
from dataclasses import replace

from .models import (
    PipelineResult, Annotation, Conflict, TypedVariable, ComplexTypeDef,
    SPLBlockType, ClarificationQuestion, SymbolTable
)
from .annotators import (
    PersonaAnnotator, AudienceAnnotator, ConceptsAnnotator,
    ConstraintsAnnotator, WorkerAnnotator
)
from .extraction import (
    VariableExtractor, TypeInferencer, TypeCollector
)
from .conflict_resolution import ConflictDetector
from .clarification import QuestionGenerator, ClarificationUI, ConsoleUI, IntentResolver
from .generators import (
    PersonaGenerator, AudienceGenerator, ConceptsGenerator,
    ConstraintsGenerator, VariablesGenerator, WorkerGenerator,
    TypesGenerator, SPLMerger
)
from .utils import BaseLLMClient, create_llm_client
from .config import OPENAI_API_KEY, OPENAI_BASE_URL, get_llm_config
from .output_manager import OutputManager, create_output_manager

logger = logging.getLogger(__name__)


class Pipeline:
    """Refactored NL2SPL Pipeline

    重构后流程：
    1. Phase 1: 并行块标注（不含VARIABLES）
    2. Phase 2: 变量提取与类型推断（新增）
    3. Phase 3: TYPES生成（优先）
    4. Phase 4: 人机交互澄清
    5. Phase 5: 分块并行生成（VARIABLES引用TYPES）
    6. Phase 6: 合并与验证（含引用验证）
    """

    def __init__(self,
                 llm_client: Optional[BaseLLMClient] = None,
                 ui: Optional[ClarificationUI] = None,
                 config: Optional[Dict] = None,
                 output_manager: Optional[OutputManager] = None):
        """初始化Pipeline

        Args:
            llm_client: LLM客户端
            ui: 澄清UI
            config: 配置
            output_manager: 输出管理器（可选，如为None则从config创建）
        """
        self.config = config or {}

        # 获取配置（优先从环境变量，其次从config字典）
        self.api_key = self.config.get('api_key') or OPENAI_API_KEY
        self.base_url = self.config.get('base_url') or OPENAI_BASE_URL or 'https://api.openai.com/v1'

        if not self.api_key:
            raise ValueError(
                "API key is required. Please set OPENAI_API_KEY in your .env file "
                "or pass it in the config."
            )

        self.llm_client = llm_client or create_llm_client({'api_key': self.api_key, 'base_url': self.base_url, 'provider': 'openai'})
        self.ui = ui or ConsoleUI()

        # 初始化输出管理器
        self.output_manager = output_manager or create_output_manager(self.config)

        # 初始化组件
        self._init_annotators()
        self._init_extractors()
        self._init_generators()
        self.conflict_detector = ConflictDetector(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.question_generator = QuestionGenerator()
        self.spl_merger = SPLMerger()

    def _init_annotators(self):
        """初始化所有标注器（不含VARIABLES）"""
        self.annotators = {
            SPLBlockType.PERSONA: PersonaAnnotator(self.llm_client),
            SPLBlockType.AUDIENCE: AudienceAnnotator(self.llm_client),
            SPLBlockType.CONCEPTS: ConceptsAnnotator(self.llm_client),
            SPLBlockType.CONSTRAINTS: ConstraintsAnnotator(self.llm_client),
            SPLBlockType.WORKER_MAIN_FLOW: WorkerAnnotator(self.llm_client),
            # ❌ 移除: SPLBlockType.VARIABLES
        }

    def _init_extractors(self):
        """初始化Phase 2提取组件（新增）"""
        self.variable_extractor = VariableExtractor(self.llm_client)
        self.type_inferencer = TypeInferencer(self.llm_client)
        self.type_collector = TypeCollector()

    def _init_generators(self):
        """初始化所有生成器（新增TypesGenerator）"""
        self.generators = {
            SPLBlockType.TYPES: TypesGenerator(self.llm_client),  # 新增
            SPLBlockType.PERSONA: PersonaGenerator(self.llm_client),
            SPLBlockType.AUDIENCE: AudienceGenerator(self.llm_client),
            SPLBlockType.CONCEPTS: ConceptsGenerator(self.llm_client),
            SPLBlockType.CONSTRAINTS: ConstraintsGenerator(self.llm_client),
            SPLBlockType.VARIABLES: VariablesGenerator(self.llm_client),
            SPLBlockType.WORKER_MAIN_FLOW: WorkerGenerator(self.llm_client),
        }

    async def convert(self, prompt: str) -> PipelineResult:
        """转换自然语言为SPL（修正后流程）

        正确流程：
        1. Phase 1: 并行块标注
        2. Phase 2: 冲突检测
        3. Phase 3: 人机交互澄清（得到最终标注）
        4. Phase 4: 从澄清后的WORKER标注提取变量
        5. Phase 5: 类型推断和TYPES生成
        6. Phase 6: 并行生成所有SPL块
        7. Phase 7: 合并与验证

        Args:
            prompt: 用户输入的自然语言描述

        Returns:
            Pipeline结果
        """
        logger.info("Starting NL to SPL conversion (corrected flow)")
        logger.info(f"Output directory: {self.output_manager.get_output_dir() if self.output_manager else 'N/A'}")

        # Phase 1: 并行块标注（不含VARIABLES）
        annotations = await self._phase1_annotation(prompt)

        # 保存 Phase 1 结果
        if self.output_manager:
            self.output_manager.save_phase1_annotations(annotations, prompt)

        # Phase 2: 冲突检测
        conflicts, clean_annotations = await self._phase2_conflict_detection(annotations)

        # 保存 Phase 2 结果
        if self.output_manager:
            self.output_manager.save_phase2_conflicts(conflicts, clean_annotations, prompt)

        # Phase 3: 人机交互澄清（关键：必须先澄清再提取变量！）
        final_annotations, clarification_history = await self._phase3_clarification(
            conflicts, clean_annotations, prompt
        )

        # 保存 Phase 3 结果
        if self.output_manager:
            self.output_manager.save_phase3_clarification(clarification_history, final_annotations, prompt)

        # Phase 4: 从澄清后的WORKER标注提取变量（修正：在澄清后提取！）
        typed_vars, complex_types = await self._phase4_extraction(
            final_annotations[SPLBlockType.WORKER_MAIN_FLOW]
        )

        # 保存 Phase 4 结果
        if self.output_manager:
            self.output_manager.save_phase4_extraction(typed_vars, complex_types, prompt)

        # Phase 5: TYPES生成
        types_block = await self._phase5_types_generation(complex_types)

        # 保存 Phase 5 结果
        if self.output_manager:
            self.output_manager.save_phase5_types(types_block, prompt)

        # Phase 6: 并行生成所有SPL块（使用澄清后的标注和变量）
        spl_blocks = await self._phase6_generation(
            final_annotations, typed_vars, types_block
        )

        # 保存 Phase 6 结果
        if self.output_manager:
            self.output_manager.save_phase6_spl_blocks(spl_blocks, prompt)

        # Phase 7: 合并与验证
        spl_code = self._phase7_merge(spl_blocks)

        # 保存最终结果
        if self.output_manager:
            self.output_manager.finalize(spl_code, prompt)

        # 构建结果
        result = PipelineResult(
            original_prompt=prompt,
            annotations=final_annotations,
            conflicts=conflicts,
            clarification_history=clarification_history,
            spl_code=spl_code,
            success=True
        )

        logger.info("NL to SPL conversion completed")
        return result

    async def _phase1_annotation(self, prompt: str) -> Dict[SPLBlockType, Annotation]:
        """Phase 1: 并行块标注（不含VARIABLES）"""
        logger.info("Phase 1: Parallel block annotation (excl. VARIABLES)")

        tasks = []
        block_types = []

        for block_type, annotator in self.annotators.items():
            task = annotator.annotate(prompt)
            tasks.append(task)
            block_types.append(block_type)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        annotations: Dict[SPLBlockType, Annotation] = {}
        for block_type, result in zip(block_types, results):
            if isinstance(result, Exception):
                logger.error(f"Annotation failed for {block_type.value}: {result}")
                annotations[block_type] = Annotation(
                    block_type=block_type,
                    segments=[],
                    confidence=0.0,
                    extracted_content=""
                )
            else:
                annotation = cast(Annotation, result)
                annotations[block_type] = annotation
                logger.info(f"Annotated {block_type.value}: {len(annotation.segments)} segments")

        return annotations

    async def _phase4_extraction(self, worker_annotation: Annotation) -> Tuple[List[TypedVariable], List[ComplexTypeDef]]:
        """Phase 4: 变量提取与类型推断（新增）"""
        logger.info("Phase 4: Variable extraction and type inference")

        if not worker_annotation or not worker_annotation.extracted_content:
            logger.warning("Empty Worker annotation, skipping extraction")
            return [], []

        # 1. 提取变量
        var_infos = await self.variable_extractor.extract(worker_annotation)
        logger.info(f"Extracted {len(var_infos)} variables")

        # 2. 推断类型
        typed_vars = await self.type_inferencer.infer(var_infos)
        logger.info(f"Inferred types for {len(typed_vars)} variables")

        # 3. 收集复杂类型
        complex_types = self.type_collector.collect(typed_vars)
        logger.info(f"Collected {len(complex_types)} complex types")

        return typed_vars, complex_types

    async def _phase5_types_generation(self, complex_types: List[ComplexTypeDef]) -> str:
        """Phase 5: TYPES生成（必须先执行）"""
        logger.info("Phase 5: TYPES generation (priority)")

        if not complex_types:
            logger.info("No complex types to generate, returning empty TYPES")
            return ""

        generator = self.generators[SPLBlockType.TYPES]
        types_block = await generator.generate(complex_types)

        logger.info(f"Generated TYPES block: {len(types_block)} chars")
        return types_block

    async def _phase2_conflict_detection(self, annotations: Dict[SPLBlockType, Annotation]) -> tuple:
        """Phase 4: 冲突检测"""
        logger.info("Phase 2: Conflict detection")

        conflicts, clean_annotations = self.conflict_detector.detect_conflicts(annotations)
        logger.info(f"Found {len(conflicts)} conflicts")

        return conflicts, clean_annotations

    async def _phase3_clarification(self,
                                    conflicts: List[Conflict],
                                    clean_annotations: Dict[SPLBlockType, Annotation],
                                    original_prompt: str) -> tuple:
        """Phase 5: 人机交互澄清"""
        logger.info("Phase 3: Clarification")

        clarification_history = []

        if not conflicts:
            logger.info("No conflicts to resolve")
            return clean_annotations, clarification_history

        # 生成问题
        questions = self.question_generator.generate_questions_batch(conflicts, original_prompt)
        logger.info(f"Generated {len(questions)} clarification questions")

        # 收集用户回答
        user_responses = await self.ui.collect_responses_batch(questions)
        logger.info(f"Collected {len(user_responses)} user responses")

        # 解析用户回答
        intent_resolver = IntentResolver(self.llm_client)
        resolution_results = await intent_resolver.resolve_batch(questions, user_responses)
        logger.info(f"Resolved {len(resolution_results)} intents")

        # 应用解决结果
        final_annotations = dict(clean_annotations)

        for result in resolution_results:
            i = result.question_index
            conflict = conflicts[i]
            resolved_label = result.selected_label

            # 记录澄清历史
            history_entry = {
                'question_index': i,
                'conflict_segments': [seg.content for seg in conflict.segments],
                'candidate_labels': [label.value for label in conflict.candidate_labels],
                'user_response': result.user_response,
                'is_other': result.is_other,
                'llm_reasoning': result.llm_reasoning,
                'resolved_label': resolved_label.value if resolved_label else None,
                'success': resolved_label is not None
            }
            clarification_history.append(history_entry)

            if resolved_label:
                # 创建解决后的标注
                resolved_annotation = self.conflict_detector.resolve_conflict(conflict, resolved_label)

                # 合并到最终结果
                if resolved_label in final_annotations:
                    existing = final_annotations[resolved_label]
                    final_annotations[resolved_label] = replace(
                        existing,
                        segments=existing.segments + resolved_annotation.segments,
                        extracted_content=existing.extracted_content + "\n\n" + resolved_annotation.extracted_content
                    )
                else:
                    final_annotations[resolved_label] = resolved_annotation

        return final_annotations, clarification_history

    async def _phase6_generation(self,
                                   annotations: Dict[SPLBlockType, Annotation],
                                   typed_vars: List[TypedVariable],
                                   types_block: str) -> Dict[SPLBlockType, str]:
        """Phase 6: 分块并行生成（VARIABLES引用TYPES）"""
        logger.info("Phase 6: Parallel block generation (VARIABLES references TYPES)")

        # 构建符号表
        type_defs = {}
        if types_block:
            # 从complex_types构建type_defs
            # 这里需要额外的解析，暂时留空
            pass

        symbol_table = SymbolTable(
            global_vars={tv.name: tv for tv in typed_vars},
            type_defs=type_defs,
            temp_vars={}
        )

        spl_blocks = {SPLBlockType.TYPES: types_block}
        tasks = []
        block_types = []

        # 首先生成VARIABLES（因为它不在annotations中，是从typed_vars生成的）
        if typed_vars:
            logger.info("Generating VARIABLES block from inferred types")
            vars_generator = self.generators[SPLBlockType.VARIABLES]
            task = vars_generator.generate_with_types(typed_vars, types_block)
            tasks.append(task)
            block_types.append(SPLBlockType.VARIABLES)

        for block_type, annotation in annotations.items():
            if not annotation.segments:
                continue

            generator = self.generators.get(block_type)
            if not generator:
                continue

            # 特殊处理：WORKER使用generate_with_symbol_table
            if block_type == SPLBlockType.WORKER_MAIN_FLOW:
                task = generator.generate_with_symbol_table(annotation, symbol_table)
            else:
                task = generator.generate(annotation)

            tasks.append(task)
            block_types.append(block_type)

        # 并行生成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for block_type, result in zip(block_types, results):
            if isinstance(result, Exception):
                logger.error(f"Generation failed for {block_type.value}: {result}")
                spl_blocks[block_type] = ""
            else:
                spl_block = cast(str, result)
                spl_blocks[block_type] = spl_block
                logger.info(f"Generated {block_type.value}: {len(spl_block)} chars")

        return spl_blocks

    def _phase7_merge(self, spl_blocks: Dict[SPLBlockType, str]) -> str:
        """Phase 7: 合并与验证"""
        logger.info("Phase 7: Merge and validation")

        spl_code = self.spl_merger.merge(spl_blocks)

        # 验证
        is_valid, errors = self.spl_merger.validate_syntax(spl_code)

        if not is_valid:
            logger.warning(f"SPL validation errors: {errors}")

        return spl_code

    @classmethod
    def from_config(cls, config_path: str) -> "Pipeline":
        """从配置文件创建Pipeline"""
        import yaml

        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        llm_config = config.get('llm', {})

        api_key = config.get('api_key') or OPENAI_API_KEY
        base_url = config.get('base_url') or OPENAI_BASE_URL or 'https://api.openai.com/v1'

        if not api_key:
            raise ValueError(
                "API key is required. Please set OPENAI_API_KEY in your .env file "
                "or in the config file."
            )

        llm_client = create_llm_client({
            'provider': llm_config.get('provider', 'openai'),
            'api_key': api_key,
            'base_url': base_url,
            'model': llm_config.get('model', 'gpt-4o'),
            'temperature': llm_config.get('temperature', 0.3),
            'max_tokens': llm_config.get('max_tokens', 4000)
        })

        return cls(llm_client=llm_client, config=config)
