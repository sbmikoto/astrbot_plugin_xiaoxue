# astrbot_plugin_xiaoxue
本插件的功能是让你的机器人能通过普通聊天一样的方式进行Comfyui工作流调用，完成画图。
最开始是用MCP来实现的，这个是插件版移植版。
似乎不是所有的LLM都可以，目前只测过gemini,claude sonnet4以及deepseek R1 0528有效
特别感谢Duikerzzz的测试

## 使用方法
插件提供了丰富的设定，配合工作流能实现各种需求。
如果实在搞不懂，也可以通过简单的设定之后，就可以画图。
sample文件夹下有更复杂的配置例子。(sample中的工作流有使用custom node，请自行安装到comfyui)

插件需要手动配置，并重启生效
- config.yaml
  插件的基础配置文件，里面有各个项目的说明。
  搞不懂的话，可以只配置server_domain和parameters的model参数。

- workflow_setting.json
  配置传入参数和工作流节点配对的设定文件，搞不懂就用默认的。
  结构是这样的
  {
    "工作流名字(可随意取)":{
        "file": 工作流文件名,
        "node_mapping": [
            "node_number": 工作流节点的编号,
                "node_property": 节点下inputs里需要设定的属性名,
                "input_param": AI传入的参数名(config.yaml里parameters设定的参数)
        ]
    }
  }

## 求助
遇到问题请发issue，或者加群752960286