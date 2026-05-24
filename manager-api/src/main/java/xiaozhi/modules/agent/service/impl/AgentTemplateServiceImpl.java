package xiaozhi.modules.agent.service.impl;

import org.springframework.stereotype.Service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;

import lombok.RequiredArgsConstructor;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.dao.AgentTemplateDao;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.entity.AgentTemplateEntity;
import xiaozhi.modules.agent.service.AgentTemplateService;

import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;

@Service
@RequiredArgsConstructor
public class AgentTemplateServiceImpl extends ServiceImpl<AgentTemplateDao, AgentTemplateEntity>
        implements AgentTemplateService {

    private final AgentDao agentDao;

    /**
     * 获取默认模板
     * 
     * @return 默认模板实体
     */
    public AgentTemplateEntity getDefaultTemplate() {
        LambdaQueryWrapper<AgentTemplateEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.orderByAsc(AgentTemplateEntity::getSort)
                .last("LIMIT 1");
        return this.getOne(wrapper);
    }

    /**
     * 更新默认模板中的模型ID
     * 
     * @param modelType 模型类型
     * @param modelId   模型ID
     */
    @Override
    public void updateDefaultTemplateModelId(String modelType, String modelId) {
        modelType = modelType.toUpperCase();
        if (modelType.equals("RAG")) {
            return;
        }

        // 读取旧模板中的模型ID，用于后续同步已有智能体
        AgentTemplateEntity oldTemplate = getDefaultTemplate();
        String oldModelId = null;
        if (oldTemplate != null) {
            oldModelId = switch (modelType) {
                case "ASR" -> oldTemplate.getAsrModelId();
                case "VAD" -> oldTemplate.getVadModelId();
                case "LLM" -> oldTemplate.getLlmModelId();
                case "TTS" -> oldTemplate.getTtsModelId();
                case "VLLM" -> oldTemplate.getVllmModelId();
                case "MEMORY" -> oldTemplate.getMemModelId();
                case "INTENT" -> oldTemplate.getIntentModelId();
                default -> null;
            };
        }

        // 更新模板表
        UpdateWrapper<AgentTemplateEntity> wrapper = new UpdateWrapper<>();
        switch (modelType) {
            case "ASR":
                wrapper.set("asr_model_id", modelId);
                break;
            case "VAD":
                wrapper.set("vad_model_id", modelId);
                break;
            case "LLM":
                wrapper.set("llm_model_id", modelId);
                break;
            case "TTS":
                wrapper.set("tts_model_id", modelId);
                wrapper.set("tts_voice_id", null);
                break;
            case "VLLM":
                wrapper.set("vllm_model_id", modelId);
                break;
            case "MEMORY":
                wrapper.set("mem_model_id", modelId);
                break;
            case "INTENT":
                wrapper.set("intent_model_id", modelId);
                break;
        }
        wrapper.ge("sort", 0);
        update(wrapper);

        // 同步所有引用旧模板模型ID的智能体，使其也切换到新模型
        if (oldModelId != null && !oldModelId.equals(modelId)) {
            String column = switch (modelType) {
                case "ASR" -> "asr_model_id";
                case "VAD" -> "vad_model_id";
                case "LLM" -> "llm_model_id";
                case "TTS" -> "tts_model_id";
                case "VLLM" -> "vllm_model_id";
                case "MEMORY" -> "mem_model_id";
                case "INTENT" -> "intent_model_id";
                default -> null;
            };

            if (column != null) {
                UpdateWrapper<AgentEntity> agentWrapper = new UpdateWrapper<>();
                agentWrapper.set(column, modelId);
                if ("TTS".equals(modelType)) {
                    agentWrapper.set("tts_voice_id", null);
                }
                agentWrapper.eq(column, oldModelId);
                agentDao.update(agentWrapper);
            }
        }
    }

    @Override
    public void reorderTemplatesAfterDelete(Integer deletedSort) {
        if (deletedSort == null) {
            return;
        }
        
        // 查询所有排序值大于被删除模板的记录
        UpdateWrapper<AgentTemplateEntity> updateWrapper = new UpdateWrapper<>();
        updateWrapper.gt("sort", deletedSort)
                    .setSql("sort = sort - 1");
        
        // 执行批量更新，将这些记录的排序值减1
        this.update(updateWrapper);
    }

    @Override
    public Integer getNextAvailableSort() {
        // 查询所有已存在的排序值并按升序排序
        List<Integer> sortValues = baseMapper.selectList(new QueryWrapper<AgentTemplateEntity>())
                .stream()
                .map(AgentTemplateEntity::getSort)
                .filter(Objects::nonNull)
                .sorted()
                .collect(Collectors.toList());
        
        // 如果没有排序值，返回1
        if (sortValues.isEmpty()) {
            return 1;
        }
        
        // 寻找最小的未使用序号
        int expectedSort = 1;
        for (Integer sort : sortValues) {
            if (sort > expectedSort) {
                // 找到空缺的序号
                return expectedSort;
            }
            expectedSort = sort + 1;
        }
        
        // 如果没有空缺，返回最大序号+1
        return expectedSort;
    }
}
