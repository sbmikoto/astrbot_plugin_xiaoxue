from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
import asyncio
from .service.call_comfy import Call_Comfy
from .utils.utils import get_config

default_model = get_config().get("comfy_model").get("default_model")
models = ",".join(get_config().get("comfy_model").get("models"))

def docstring_parameter(*args, **kwargs):
    """创建一个可以添加变量的 docstring 装饰器"""
    def decorator(obj):
        obj.__doc__ = obj.__doc__.format(*args, **kwargs)
        return obj
    return decorator

@register("test", "sbmikoto", "小雪", "0.0.1", "local")
class MyPlugin(Star):
  def __init__(self, context: Context):
    super().__init__(context)

  @filter.llm_tool(name="generate_image_test")
  @docstring_parameter(default_model, models)
  async def generate_image_test(self, event: AstrMessageEvent, prompt: str, width: int = 1024, height: int = 1024, model: str = "oneObsession_13", cfg: float = 5) -> MessageEventResult:
    '''根据用户需求生成图片, 通过上下文判断用户需要图片生成的时候调用。

    Args:
      prompt(string): 需要把用户的需求翻译成danbooru的tag形式，要选用danbooru.donmai.us里存在的tag，作为输入参数。需要注意，tag不需要带下划线，并且需要保留\符号
      width(number): 根据图片需求设定合适的宽度，范围是768-1536, 用户可以自定义。
      height(number): 根据图片需求设定合适的高度，范围是768-1536, 用户可以自定义。
      model(string): 默认为{0}，如果用户指明了模型名，就在{1}中选择最接近的。
      cfg(number): 默认为5,以0.5为单位，用户可以自定义。
    '''

    info = {
      "prompt": prompt,
      "width": width,
      "height": height,
      "model": model + ".safetensors",
      "cfg": cfg
    }

    asyncio.create_task(Call_Comfy().generate_image(info, self, event.unified_msg_origin))
    yield event.plain_result(" 努力画图中喵ing♡~~~ ")


