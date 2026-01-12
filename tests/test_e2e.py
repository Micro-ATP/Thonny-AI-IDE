"""
AI Completion Plugin - 端到端测试脚本
=====================================

测试整个插件流程：配置 → 补全请求 → 结果显示 → 错误处理

使用方法：
    python tests/test_e2e.py

作者: AI Completion Group 1
版本: 1.0.0
"""

import unittest
import sys
import os
import json
import tempfile
import time
from unittest.mock import Mock, MagicMock, patch
from io import StringIO

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestE2EConfigFlow(unittest.TestCase):
    """端到端测试：配置流程"""
    
    def test_config_create_and_load(self):
        """测试配置文件的创建和加载"""
        try:
            from thonnycontrib.ai_completion.ai_config import AICompletionConfig
            
            # 创建临时配置目录
            with tempfile.TemporaryDirectory() as temp_dir:
                # Mock 配置路径
                with patch.object(AICompletionConfig, '_get_config_path', 
                                  return_value=os.path.join(temp_dir, 'config.json')):
                    config = AICompletionConfig()
                    
                    # 验证默认配置
                    self.assertTrue(config.is_enabled())
                    self.assertIsNotNone(config.get_ai_service_config())
                    
                    # 修改配置
                    config.set_enabled(False)
                    config.set_ai_service_config(
                        api_key="test-key-12345",
                        endpoint="https://test.api.com/v1",
                        model="test-model"
                    )
                    
                    # 保存配置
                    success = config.save_config()
                    self.assertTrue(success)
                    
                    # 验证文件已创建
                    self.assertTrue(os.path.exists(os.path.join(temp_dir, 'config.json')))
                    
                    # 重新加载配置
                    config2 = AICompletionConfig()
                    with patch.object(config2, '_get_config_path', 
                                      return_value=os.path.join(temp_dir, 'config.json')):
                        config2.reload_config()
                    
                    print("✓ 配置创建和加载测试通过")
                    
        except ImportError as e:
            self.skipTest(f"无法导入配置模块: {e}")
    
    def test_config_validation(self):
        """测试配置验证"""
        try:
            from thonnycontrib.ai_completion.ai_config import AICompletionConfig
            
            config = AICompletionConfig()
            
            # 验证默认值
            context_config = config.get_context_config()
            self.assertIn("lines_before", context_config)
            self.assertIn("lines_after", context_config)
            self.assertIn("max_chars", context_config)
            
            # 验证数值范围
            self.assertGreater(context_config["lines_before"], 0)
            self.assertGreater(context_config["lines_after"], 0)
            self.assertGreater(context_config["max_chars"], 0)
            
            print("✓ 配置验证测试通过")
            
        except ImportError as e:
            self.skipTest(f"无法导入配置模块: {e}")


class TestE2ECompletionFlow(unittest.TestCase):
    """端到端测试：补全流程"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_response = {
            "choices": [{
                "message": {
                    "content": "def hello():\n    print('Hello, World!')"
                }
            }]
        }
    
    @patch('requests.post')
    def test_completion_request_success(self, mock_post):
        """测试成功的补全请求"""
        try:
            from thonnycontrib.ai_completion.ai_client import AIClient
            
            # Mock API 响应
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = self.mock_response
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            # 创建客户端
            client = AIClient(
                api_key="test-key",
                endpoint="https://test.api.com/v1/chat/completions",
                model="test-model"
            )
            
            # 发送请求
            context = {
                "text": "def hello",
                "prefix": "def hello",
                "suffix": "",
                "language": "python",
                "mode": "completion"
            }
            
            result = client.request(context)
            
            # 验证结果
            self.assertTrue(result.get("success"))
            self.assertIn("data", result)
            self.assertIn("raw_analysis", result["data"])
            
            print("✓ 成功补全请求测试通过")
            
        except ImportError as e:
            self.skipTest(f"无法导入 AI 客户端模块: {e}")
    
    @patch('requests.post')
    def test_completion_request_api_error(self, mock_post):
        """测试 API 错误处理"""
        try:
            from thonnycontrib.ai_completion.ai_client import AIClient
            import requests
            
            # Mock 401 错误
            mock_post.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
            
            client = AIClient(
                api_key="invalid-key",
                endpoint="https://test.api.com/v1/chat/completions",
                model="test-model"
            )
            
            context = {
                "text": "test",
                "prefix": "test",
                "suffix": "",
                "language": "python",
                "mode": "completion"
            }
            
            result = client.request(context)
            
            # 验证错误处理
            self.assertFalse(result.get("success"))
            self.assertIn("message", result)
            
            print("✓ API 错误处理测试通过")
            
        except ImportError as e:
            self.skipTest(f"无法导入 AI 客户端模块: {e}")
    
    @patch('requests.post')
    def test_completion_request_timeout(self, mock_post):
        """测试请求超时处理"""
        try:
            from thonnycontrib.ai_completion.ai_client import AIClient
            import requests
            
            # Mock 超时
            mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")
            
            client = AIClient(
                api_key="test-key",
                endpoint="https://test.api.com/v1/chat/completions",
                model="test-model"
            )
            
            context = {
                "text": "test",
                "prefix": "test",
                "suffix": "",
                "language": "python",
                "mode": "completion"
            }
            
            result = client.request(context)
            
            # 验证超时处理
            self.assertFalse(result.get("success"))
            msg = result.get("message", "").lower()
            self.assertTrue("timeout" in msg or "timed out" in msg)
            
            print("✓ 请求超时处理测试通过")
            
        except ImportError as e:
            self.skipTest(f"无法导入 AI 客户端模块: {e}")


class TestE2EContextHandling(unittest.TestCase):
    """端到端测试：上下文处理"""
    
    def test_context_extraction_basic(self):
        """测试基本上下文提取"""
        try:
            from thonnycontrib.ai_completion.completion_handler import ContextExtractor
            
            # 创建 Mock text_widget
            mock_widget = Mock()
            
            # 模拟代码内容
            code = """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(10)
print(result)"""
            
            lines = code.split('\n')
            
            # 模拟光标在第 6 行开头
            mock_widget.index.return_value = "6.0"
            mock_widget.get.side_effect = lambda start, end: self._mock_get(code, start, end)
            
            # 由于完整测试需要真实 widget，这里只验证类存在
            self.assertTrue(hasattr(ContextExtractor, 'extract_context'))
            print("✓ 上下文提取类测试通过")
            
        except ImportError as e:
            self.skipTest(f"无法导入上下文处理模块: {e}")
    
    def _mock_get(self, code, start, end):
        """模拟 text_widget.get()"""
        if end == "end-1c":
            return code
        return code


class TestE2EErrorRecovery(unittest.TestCase):
    """端到端测试：错误恢复"""
    
    def test_missing_config_recovery(self):
        """测试配置缺失时的恢复"""
        try:
            from thonnycontrib.ai_completion.ai_config import AICompletionConfig
            
            # 创建配置实例（使用默认值）
            config = AICompletionConfig()
            
            # 验证默认配置可用
            self.assertIsNotNone(config.get_ai_service_config())
            self.assertIsNotNone(config.get_context_config())
            
            print("✓ 配置缺失恢复测试通过")
            
        except ImportError as e:
            self.skipTest(f"无法导入配置模块: {e}")
    
    def test_invalid_json_recovery(self):
        """测试无效 JSON 配置的恢复"""
        try:
            from thonnycontrib.ai_completion.ai_config import AICompletionConfig
            
            with tempfile.TemporaryDirectory() as temp_dir:
                config_path = os.path.join(temp_dir, 'config.json')
                
                # 写入无效 JSON
                with open(config_path, 'w') as f:
                    f.write("{ invalid json }")
                
                # Mock 配置路径
                with patch.object(AICompletionConfig, '_get_config_path', 
                                  return_value=config_path):
                    config = AICompletionConfig()
                    
                    # 应该使用默认配置
                    self.assertTrue(config.is_enabled())
                    
                    print("✓ 无效 JSON 恢复测试通过")
                    
        except ImportError as e:
            self.skipTest(f"无法导入配置模块: {e}")


class TestE2EStateManagement(unittest.TestCase):
    """端到端测试：状态管理"""
    
    def test_state_transitions(self):
        """测试状态转换"""
        try:
            from thonnycontrib.ai_completion.main import (
                REQUEST_STATE_IDLE,
                REQUEST_STATE_REQUESTING,
                REQUEST_STATE_SHOWING,
                _request_lock
            )
            
            # 验证状态常量
            states = [REQUEST_STATE_IDLE, REQUEST_STATE_REQUESTING, REQUEST_STATE_SHOWING]
            self.assertEqual(len(set(states)), 3, "状态值应该唯一")
            
            # 验证锁可用
            with _request_lock:
                pass  # 成功获取和释放锁
            
            print("✓ 状态管理测试通过")
            
        except ImportError as e:
            self.skipTest(f"无法导入 main 模块: {e}")


class TestE2ECleanup(unittest.TestCase):
    """端到端测试：清理功能"""
    
    def test_completion_cleanup(self):
        """测试补全响应清理"""
        try:
            from thonnycontrib.ai_completion.ai_client import AIClient
            
            client = AIClient.__new__(AIClient)
            client.api_key = None
            client.endpoint = ""
            client.model = ""
            
            # 测试 Markdown 清理
            response_with_md = "```python\ndef hello():\n    pass\n```"
            cleaned = client._clean_completion(response_with_md, "completion", "", "")
            self.assertNotIn("```", cleaned)
            
            # 测试前导空格清理
            response_with_spaces = "   def hello():\n    pass"
            cleaned = client._clean_completion(response_with_spaces, "completion", "", "")
            # 验证前导空格被清理，代码结构保持
            self.assertTrue(cleaned.strip().startswith("def hello()"))
            self.assertIn("pass", cleaned)
            
            print("✓ 补全清理测试通过")
            
        except ImportError as e:
            self.skipTest(f"无法导入 AI 客户端模块: {e}")


def run_e2e_tests():
    """运行所有端到端测试"""
    print("=" * 60)
    print("AI Completion Plugin - 端到端测试")
    print("=" * 60)
    print()
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestE2EConfigFlow,
        TestE2ECompletionFlow,
        TestE2EContextHandling,
        TestE2EErrorRecovery,
        TestE2EStateManagement,
        TestE2ECleanup,
    ]
    
    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 打印摘要
    print()
    print("=" * 60)
    print("端到端测试摘要")
    print("=" * 60)
    print(f"运行测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_e2e_tests()
    sys.exit(0 if success else 1)

