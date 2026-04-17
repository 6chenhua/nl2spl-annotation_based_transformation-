"""主Pipeline

协调整个NL到SPL的转换流程。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, cast
from dataclasses import replace

from .models import (
    PipelineResult, Annotation, Conflict,
    SPLBlockType, ClarificationQuestion
)
from .annotators import (
    PersonaAnnotator, AudienceAnnotator, ConceptsAnnotator,
    ConstraintsAnnotator, VariablesAnnotator, WorkerAnnotator
)
from .conflict_resolution import ConflictDetector
from .clarification import QuestionGenerator, ClarificationUI, ConsoleUI, LabelMapper, IntentResolver
from .generators import (
    PersonaGenerator, AudienceGenerator, ConceptsGenerator,
    ConstraintsGenerator, VariablesGenerator, WorkerGenerator, SPLMerger
)
from .utils import BaseLLMClient, create_llm_client
from .config import OPENAI_API_KEY, OPENAI_BASE_URL, get_llm_config

logger = logging.getLogger(__name__)


class Pipeline:
    """Annotated NL2SPL Pipeline

    5阶段流程：
    1. 并行块标注
    2. 冲突检测与聚合
    3. 人机交互澄清
    4. 分块并行生成
    5. 合并与验证
    """

    def __init__(self,
                 llm_client: Optional[BaseLLMClient] = None,
                 ui: Optional[ClarificationUI] = None,
                 config: Optional[Dict] = None):
        """初始化Pipeline

        Args:
            llm_client: LLM客户端
            ui: 澄清UI
            config: 配置
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

        # 初始化组件
        self._init_annotators()
        self._init_generators()
        self.conflict_detector = ConflictDetector(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.question_generator = QuestionGenerator()
        self.spl_merger = SPLMerger()
        
    def _init_annotators(self):
        """初始化所有标注器"""
        self.annotators = {
            SPLBlockType.PERSONA: PersonaAnnotator(self.llm_client),
            SPLBlockType.AUDIENCE: AudienceAnnotator(self.llm_client),
            SPLBlockType.CONCEPTS: ConceptsAnnotator(self.llm_client),
            SPLBlockType.CONSTRAINTS: ConstraintsAnnotator(self.llm_client),
            SPLBlockType.VARIABLES: VariablesAnnotator(self.llm_client),
            SPLBlockType.WORKER_MAIN_FLOW: WorkerAnnotator(self.llm_client),
        }
    
    def _init_generators(self):
        """初始化所有生成器"""
        self.generators = {
            SPLBlockType.PERSONA: PersonaGenerator(self.llm_client),
            SPLBlockType.AUDIENCE: AudienceGenerator(self.llm_client),
            SPLBlockType.CONCEPTS: ConceptsGenerator(self.llm_client),
            SPLBlockType.CONSTRAINTS: ConstraintsGenerator(self.llm_client),
            SPLBlockType.WORKER_MAIN_FLOW: WorkerGenerator(self.llm_client),
        }
    
    async def convert(self, prompt: str) -> PipelineResult:
        """转换自然语言为SPL
        
        Args:
            prompt: 用户输入的自然语言描述
            
        Returns:
            Pipeline结果
        """
        logger.info("Starting NL to SPL conversion")
        
        # Phase 1: 并行块标注
        annotations = await self._phase1_annotation(prompt)
        
        # Phase 2: 冲突检测
        conflicts, clean_annotations = await self._phase2_conflict_detection(
            annotations
        )
        
        # Phase 3: 人机交互澄清
        final_annotations, clarification_history = await self._phase3_clarification(
            conflicts, clean_annotations, prompt
        )

        # Phase 4: 分块生成
        spl_blocks = await self._phase4_generation(final_annotations)

        # Phase 5: 合并
        spl_code = self._phase5_merge(spl_blocks)

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
        """Phase 1: 并行块标注"""
        logger.info("Phase 1: Parallel block annotation")
        
        # 并行执行所有标注器
        tasks = []
        block_types = []
        
        for block_type, annotator in self.annotators.items():
            task = annotator.annotate(prompt)
            tasks.append(task)
            block_types.append(block_type)
        
        # 等待所有标注完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集结果
        annotations: Dict[SPLBlockType, Annotation] = {}
        for block_type, result in zip(block_types, results):
            if isinstance(result, Exception):
                logger.error(f"Annotation failed for {block_type.value}: {result}")
                # 创建空标注
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
    
    async def _phase2_conflict_detection(self, annotations: Dict[SPLBlockType, Annotation]) -> tuple:
        """Phase 2: 冲突检测"""
        logger.info("Phase 2: Conflict detection")
        
        conflicts, clean_annotations = self.conflict_detector.detect_conflicts(annotations)
        
        logger.info(f"Found {len(conflicts)} conflicts")
        
        return conflicts, clean_annotations
    
    async def _phase3_clarification(self,
                                    conflicts: List[Conflict],
                                    clean_annotations: Dict[SPLBlockType, Annotation],
                                    original_prompt: str) -> tuple:
        """Phase 3: 人机交互澄清

        新流程：
        1. 并行收集所有用户回答（UI层）
        2. 批量异步LLM处理"其他"选项
        3. 应用解决结果

        Returns:
            (final_annotations, clarification_history)
        """
        logger.info("Phase 3: Clarification")

        clarification_history = []

        if not conflicts:
            logger.info("No conflicts to resolve")
            return clean_annotations, clarification_history

        # 生成问题
        questions = self.question_generator.generate_questions_batch(
            conflicts, original_prompt
        )

        logger.info(f"Generated {len(questions)} clarification questions")

        # 阶段1: 收集用户回答（仅UI交互，无LLM调用）
        user_responses = await self.ui.collect_responses_batch(questions)
        logger.info(f"Collected {len(user_responses)} user responses")

        # 阶段2: 批量解析用户回答（异步LLM处理"其他"选项）
        intent_resolver = IntentResolver(self.llm_client)
        resolution_results = await intent_resolver.resolve_batch(questions, user_responses)
        logger.info(f"Resolved {len(resolution_results)} intents")

        # 阶段3: 应用解决结果
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
                resolved_annotation = self.conflict_detector.resolve_conflict(
                    conflict, resolved_label
                )

                # 合并到最终结果
                if resolved_label in final_annotations:
                    # 追加内容
                    existing = final_annotations[resolved_label]
                    final_annotations[resolved_label] = replace(
                        existing,
                        segments=existing.segments + resolved_annotation.segments,
                        extracted_content=existing.extracted_content + "\n\n" + resolved_annotation.extracted_content
                    )
                else:
                    final_annotations[resolved_label] = resolved_annotation

        return final_annotations, clarification_history
    
    async def _phase4_generation(self, 
                                 annotations: Dict[SPLBlockType, Annotation]) -> Dict[SPLBlockType, str]:
        """Phase 4: 分块并行生成"""
        logger.info("Phase 4: Parallel block generation")
        
        spl_blocks = {}
        tasks = []
        block_types = []
        
        for block_type, annotation in annotations.items():
            if block_type in self.generators and annotation.segments:
                task = self.generators[block_type].generate(annotation)
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
    
    def _phase5_merge(self, spl_blocks: Dict[SPLBlockType, str]) -> str:
        """Phase 5: 合并与验证"""
        logger.info("Phase 5: Merge and validation")
        
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
        
        # 优先从环境变量读取API key，其次从配置文件
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