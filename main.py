from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
import asyncio
import inspect
from .service.call_comfy import Call_Comfy
from .utils.utils import get_config_section

start_message = get_config_section("messages").get("start_message", "开始画图")

def dynamic_params(param_configs):
    """
    动态修改函数参数的装饰器
    param_configs: [{name:"", type:"",description:"",workflow:""}]
    """
    def decorator(func):
        # 获取原始函数的签名
        original_sig = inspect.signature(func)
        original_params = list(original_sig.parameters.values())
        original_doc = inspect.getdoc(func)
        
        # 创建新的参数列表
        new_params = []
        new_params_doc = []
        
        # 保留前两个固定参数 (self, event)
        new_params.extend(original_params[:2])
        
        # 添加动态参数
        for param in param_configs:
            param_type = param.get('type', str)
            default_value = param.get('default', inspect.Parameter.empty)
            
            param_name = param.get('name')
            new_param = inspect.Parameter(
                param_name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                default=default_value,
                annotation=param_type
            )
            new_params.append(new_param)

            json_type = "string"
            if param_type in ["int", "float"]:
               json_type = "number"
            elif param_type == "bool":
               json_type = "boolean"

            new_param_doc = f"  {param_name}({json_type}): {param.get('description')}" 
            new_params_doc.append(new_param_doc)
        
        # 创建新的函数签名
        new_sig = original_sig.replace(parameters=new_params)
        func.__signature__ = new_sig

        join_params_doc = '\n'.join(new_params_doc)
        final_docstring = f"{original_doc}\n{join_params_doc}"

        func.__doc__ = final_docstring
        
        return func
    return decorator

@register("test", "sbmikoto", "小雪", "0.0.2", "local")
class MyPlugin(Star):
  def __init__(self, context: Context):
    super().__init__(context)

  @filter.llm_tool(name="generate_image_test")
  @dynamic_params(get_config_section("parameters"))
  async def generate_image_test(self, event: AstrMessageEvent, **kwargs) -> MessageEventResult:
    '''根据用户需求生成图片, 通过上下文判断用户需要图片生成的时候调用。

    Args:
    '''
    # 构建默认值
    default_info = {}
    for param in get_config_section("parameters"):
       param_name = param.get("name")
       param_default_value = param.get("default")
       if param_name and param_default_value is not None:
          default_info[param_name] = param_default_value

    info = {**default_info, **kwargs}

    print(info)

    asyncio.create_task(Call_Comfy().generate_image(info, self, event.unified_msg_origin))
    yield event.plain_result(start_message)
    return_to_llm = "告诉用户正在画图中"
    yield return_to_llm