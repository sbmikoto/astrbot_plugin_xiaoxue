import os
import json
import uuid
import yaml

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data/workflow/workflow_setting.json")
config = None

def get_config():
    global config
    if not config:
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.yaml")
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    return config

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