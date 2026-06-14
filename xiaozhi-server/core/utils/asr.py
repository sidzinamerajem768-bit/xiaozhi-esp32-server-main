import importlib
import logging
import os
import sys
import time
import wave
import uuid
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# ASR 类型别名映射：配置中可能使用的旧名称/错误名称 -> 实际模块文件名
_ASR_TYPE_ALIASES = {
    "CozeStreamASR": "coze_stream",
}


def create_instance(class_name: str, *args, **kwargs) -> ASRProviderBase:
    """工厂方法创建ASR实例"""
    # 先通过别名映射解析实际模块名
    module_name = _ASR_TYPE_ALIASES.get(class_name, class_name)
    if os.path.exists(os.path.join('core', 'providers', 'asr', f'{module_name}.py')):
        lib_name = f'core.providers.asr.{module_name}'
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(f'{lib_name}')
        return sys.modules[lib_name].ASRProvider(*args, **kwargs)

    raise ValueError(f"不支持的ASR类型: {class_name}，请检查该配置的type是否设置正确")