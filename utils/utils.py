import os
import json
import uuid
import yaml
import re

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data/workflow/workflow_setting.json")
config = None

def get_config():
    global config
    if not config:
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.yaml")
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    return config

def get_config_section(section: str):
    return get_config().get(section)

def get_workflow_settings(name):
    try:
        if not os.path.exists(CONFIG_FILE_PATH):
            print(f"错误：配置文件 '{CONFIG_FILE_PATH}' 未找到。")
            return None
        
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if name in data:
            return data[name]
        else:
            print(f"错误：在配置文件中未找到名为 '{name}' 的工作流设置。")
            return None
        
    except Exception as e:
        print(f"获取工作流设置时发生未知错误：{e}")
        return None
    
def create_workflow(json_info, input_params):
    try:
        workflow_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", f"data/workflow/{json_info['file']}.json")
        if not os.path.exists(workflow_file):
            print(f"错误：工作流文件 '{workflow_file}' 未找到。")
            return None
        
        with open(workflow_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for item in json_info['node_mapping']:
            v = None
            if item['input_param'] == "random_seed":
                v = uuid.uuid4().int & (1<<32)-1
            else:
                v = input_params.get(item['input_param'])

            if v:
                try:
                    data[item['node_number']]['inputs'][item['node_property']] = v
                except KeyError as e:
                    print(f"错误：设置的键值对有问题 '{v}' 请仔细检查。")
                    pass
        
        return data
    
    except Exception as e:
        print(f"创建工作流时发生错误：{e}")
        return None
    
def evaluate_custom_rule(rule_str: str, info: dict) -> bool:
    """
    评估自定义规则字符串。

    :param rule_str: 用户定义的规则字符串。
                     例如: "c&&d,1" 或 "(b||d,2)&&c"
    :param info: 包含变量值的字典。
                 例如: {"a": "123", "b": "234", "c": True, "d": 2}
    :return: 规则评估结果 (True 或 False)。
    :raises ValueError: 如果规则字符串包含无效语法或评估时出错。
    """
    # 内部辅助函数，用于评估单个条件 (例如 "c" 或 "d,1")
    def _check_condition_internal(condition_item_str: str) -> bool:
        nonlocal info # 使用外部函数作用域的info字典
        
        parts = condition_item_str.split(',', 1)
        key = parts[0].strip()

        if key not in info:
            # print(f"警告: 键 '{key}' 在 info 字典中未找到。")
            return False  # 如果键不存在，条件为假

        actual_value = info[key]

        if len(parts) == 1:  # 例如 "c" - 检查真实性/是否有值
            # "当c为真(或者有值)"
            if isinstance(actual_value, str):
                return actual_value != ""  # 空字符串为False，非空为True
            return bool(actual_value) # 其他类型直接用bool()判断
        else:  # 例如 "d,1" - 检查是否等于特定值
            expected_value_str = parts[1].strip()
            
            try:
                if isinstance(actual_value, bool):
                    # 对于布尔类型的实际值，期望值也应被解释为布尔型
                    if expected_value_str.lower() == 'true':
                        expected_value = True
                    elif expected_value_str.lower() == 'false':
                        expected_value = False
                    else:
                        # print(f"警告: 无法将 '{expected_value_str}' 与布尔值进行比较。")
                        return False # 无法识别的布尔字符串
                elif isinstance(actual_value, int):
                    expected_value = int(expected_value_str)
                elif isinstance(actual_value, float):
                    expected_value = float(expected_value_str)
                elif isinstance(actual_value, str):
                    expected_value = expected_value_str # 字符串直接比较
                else:
                    # 对于其他未知类型，尝试将实际值转为字符串进行比较
                    # print(f"警告: 尝试将类型 {type(actual_value)} 的值与字符串 '{expected_value_str}' 进行比较。")
                    return str(actual_value) == expected_value_str
                
                return actual_value == expected_value
            except ValueError:
                # print(f"警告: 为键 '{key}' 比较时，值 '{expected_value_str}' 类型转换失败。")
                # 如果类型转换失败 (例如，试图将 "abc" 转为整数与一个整数比较)，则条件为假
                return False
            except Exception as e:
                # print(f"警告: 在比较 '{condition_item_str}' 时发生错误: {e}")
                return False # 其他比较错误
    # 1. 分词 (Tokenize)
    tokens = []
    i = 0
    rule_len = len(rule_str)
    while i < rule_len:
        char = rule_str[i]
        if char.isspace():
            i += 1
            continue
        elif char == '(':
            tokens.append({'type': 'LPAREN', 'value': '('})
            i += 1
        elif char == ')':
            tokens.append({'type': 'RPAREN', 'value': ')'})
            i += 1
        elif rule_str.startswith("&&", i):
            tokens.append({'type': 'AND', 'value': 'and'}) # Python的 'and'
            i += 2
        elif rule_str.startswith("||", i):
            tokens.append({'type': 'OR', 'value': 'or'})   # Python的 'or'
            i += 2
        else:
            # 匹配条件部分，如 "c" 或 "d,1"
            # 变量名: 以字母或下划线开头，后跟字母、数字或下划线
            # 值部分: 逗号后跟着非特殊字符 (非括号、空格、&、|)
            # 这个正则表达式匹配 "var" 或 "var,value"
            match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*(?:,[^()\s&|]+)?)", rule_str[i:])
            if match:
                condition_text = match.group(1)
                tokens.append({'type': 'COND', 'value': condition_text})
                i += len(condition_text)
            else:
                raise ValueError(f"规则字符串中存在无法解析的字符或结构: '{rule_str[i:]}'")
            
    # 2. 转换 (Transform) 成 Python 可执行的表达式字符串
    py_eval_str_parts = []
    for token in tokens:
        if token['type'] == 'COND':
            # 将 "c" 变成 "_check_condition_internal(\"c\")"
            # 注意处理条件字符串中的引号 (虽然当前规则值不允许引号)
            escaped_cond_value = token['value'].replace('"', '\\"') 
            py_eval_str_parts.append(f'_check("{escaped_cond_value}")')
        else:
            py_eval_str_parts.append(token['value']) # "and", "or", "(", ")"
    
    py_eval_str = " ".join(py_eval_str_parts)

    # 3. 安全执行 (Safe Evaluation)
    # 构建eval的执行环境，限制可用的内建函数和全局变量
    eval_globals = {
        "__builtins__": {"True": True, "False": False, "None": None}, # 非常有限的内建函数
        "_check": _check_condition_internal  # 暴露我们的条件检查函数
    }

    try:
        result = eval(py_eval_str, eval_globals, {}) # locals为空字典
        return bool(result)
    except SyntaxError as e:
        raise ValueError(f"转换后的规则表达式存在语法错误: '{py_eval_str}'. 错误: {e}") from e
    except Exception as e:
        # 其他在eval过程中可能发生的错误 (例如 _check 本身抛出未捕获的异常)
        raise ValueError(f"评估规则 '{rule_str}' (转换后为 '{py_eval_str}') 时出错: {e}") from e