import uuid
import aiohttp
import json
import os
import io
import ssl
import certifi
from astrbot.api.event import MessageChain
from ..utils.utils import get_workflow_settings, create_workflow, get_config_section, evaluate_custom_rule

class Call_Comfy:
    CLIENT_ID = str(uuid.uuid4())
    SERVER_URL = get_config_section('comfy').get('url_header') + "://" + get_config_section('comfy').get('server_domain')
    WS_HEADER = "ws" if get_config_section('comfy').get('url_header') == "http" else "wss"
    SERVER_WS_URL = WS_HEADER + "://" + get_config_section('comfy').get('server_domain')
    OUTPUT_IMAGE_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data/output")
    DEFAULT_WORKFLOW = get_config_section('comfy').get('default_workflow')

    async def generate_image(self, info, astr_self, unified_msg_origin):
        image_url = info.get("send_image")
        if image_url:
            image_filename = info.get("send_image_key") + ".png"
            await self.upload_image(image_url, image_filename)
            del info["send_image_key"]
            info["send_image"] = image_filename
        workflow_setting = get_workflow_settings(self.get_workflow(info))
        model_name = info.get("model")
        if model_name:
            info["model"] = model_name + "." + self.get_model_fullname(model_name)
        promptWorkflow = create_workflow(workflow_setting, info)
        queued_prompt_info = await self.queue_prompt(promptWorkflow)
        prompt_id = queued_prompt_info["prompt_id"]
        image_file = await self.track_progress_and_get_images(prompt_id)

        complete_msg_setting = get_config_section('messages').get('complete_message')
        complete_msg = " 图片完成 \n"
        if complete_msg_setting:
            complete_msg_base = complete_msg_setting.get("base_string")
            if complete_msg_base:
                complete_msg = complete_msg_base + "\n"
                addition = complete_msg_setting.get("addtion")
                if addition:
                    for key, value in addition.items():
                        info_value = info.get(key)
                        if info_value:
                            complete_msg = complete_msg + value + str(info_value) + "\n"

        message_chain = MessageChain().message(complete_msg).file_image(image_file)
        await astr_self.context.send_message(unified_msg_origin, message_chain)

    async def upload_image(self, image_url, filename):
        image_content = None
        content_type = 'image/png'
        image_url = image_url.replace("https://", "http://")
        try:
            #下载图片
            ssl_context_download = ssl.create_default_context(cafile=certifi.where())
            connector_download = aiohttp.TCPConnector(ssl=ssl_context_download)
            async with aiohttp.ClientSession(connector=connector_download, trust_env=True) as session_download:
                async with session_download.get(image_url) as resp_download:
                    resp_download.raise_for_status()
                    image_content = await resp_download.read()
                    content_type = resp_download.headers.get('Content-Type', 'image/png')

        except (aiohttp.ClientConnectorSSLError, aiohttp.ClientConnectorCertificateError) as ssl_error:
            async with aiohttp.ClientSession(trust_env=True) as session_download_fallback:
                async with session_download_fallback.get(image_url, ssl=False) as resp_download_fallback: # ssl=False 禁用SSL验证
                    resp_download_fallback.raise_for_status()
                    image_content = await resp_download_fallback.read()
                    content_type = resp_download_fallback.headers.get('Content-Type', 'image/png')
        except aiohttp.ClientResponseError as http_error: # 处理下载时的HTTP错误
            print(f"图片下载失败 (HTTP错误): {http_error.status} {http_error.message} 从 {image_url}")
            raise http_error
        except Exception as e: # 其他下载错误
            print(f"图片下载时发生未知错误: {e} 从 {image_url}")
            raise e
        
        if image_content is None:
            raise ValueError(f"无法从 {image_url} 下载图片内容")
        
        #上传到comfy
        try:
            upload_url = f"{self.SERVER_URL}/upload/image"
            form_data = aiohttp.FormData()
            form_data.add_field(
                'image',
                io.BytesIO(image_content), # 将bytes包装在BytesIO中
                filename=filename,
                content_type=content_type
            )
            form_data.add_field('overwrite', 'true')

            async with aiohttp.ClientSession(trust_env=True) as session_upload:
                async with session_upload.post(upload_url, data=form_data) as resp_upload:
                    resp_upload.raise_for_status()

        except Exception as error:
            print(f'图片上传失败: {error}')
            raise error

    def get_workflow(self, info):
        workflow = self.DEFAULT_WORKFLOW

        #取得工作流设定
        workflow_settings = get_config_section("switch_workflow")
        if workflow_settings:
            for workflow_setting in workflow_settings:
                workflow_name = workflow_setting.get("workflow_name")
                if not workflow_name:
                    pass
                check = False
                workflow_models = workflow_setting.get("model")
                model_name = info.get("model")
                if workflow_models and model_name:
                    workflow_models_split = workflow_models.split(",")
                    if model_name in workflow_models_split:
                        check = True
                workflow_param_rule = workflow_setting.get("param_rule")
                if workflow_param_rule:
                    try:
                        check = evaluate_custom_rule(workflow_param_rule, info)
                    except Exception as e:
                        print(f"规则判断发生错误: {e}")
                        check = False
                
                if check:
                    workflow = workflow_name

        return workflow
    
    def get_model_fullname(self, model: str):
        config_models = get_config_section("comfy_models")
        for config_model in config_models:
            if config_model["name"] == model:
                type = config_model.get("type") if config_model.get("type") else "safetensors"
                return type
        return "safetensors"

    async def queue_prompt(self, workflow):
        payload = {
            "prompt": workflow,
            "client_id": self.CLIENT_ID
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.SERVER_URL}/prompt", json=payload) as response:
                response_data = await response.json()
                status_code = response.status
                if response_data:
                    if "prompt_id" in response_data:
                        print(f"工作流程已成功提交! Prompt ID: {response_data['prompt_id']}")
                        return response_data
    
    async def get_history(self, prompt_id):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.SERVER_URL}/history/{prompt_id}") as response:
                if response.status == 200:
                    history_data = await response.json()
                    return history_data
                
    async def get_image(self, filename, subfolder, folder_type):
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.SERVER_URL}/view", params=params) as response:
                if response.status == 200:
                    return await response.read()


    async def track_progress_and_get_images(self, prompt_id):

        ws_url = f"{self.SERVER_WS_URL}/ws?clientId={self.CLIENT_ID}"

        output_images_details = []
        prompt_done = False #暂时没用

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                              
                        message_data = json.loads(msg.data)
                        if "type" in message_data:
                            msg_type = message_data["type"]
                            data = message_data.get("data", {})

                            if msg_type == "status":
                                queue_remaining = data.get("status", {}).get("execinfo", {}).get("queue_remaining", 0)
                                print(f"队列状态更新: 剩余任务 {queue_remaining}")
                                if queue_remaining == 0 and data.get("status", {}).get("execinfo", {}).get("prompt_id") == prompt_id:
                                    pass

                            elif msg_type == "execution_start":
                                if data.get("prompt_id") == prompt_id:
                                    print(f"Prompt {prompt_id} 开始执行...")

                            elif msg_type == "execution_cached":
                                if data.get("prompt_id") == prompt_id:
                                    print(f"Prompt {prompt_id} 的结果从缓存加载。节点: {data.get('nodes')}")

                            elif msg_type == "executing":
                                current_prompt_id = data.get("prompt_id")
                                node_id = data.get("node")
                                if current_prompt_id == prompt_id:
                                    if node_id is None:
                                        print(f"Prompt {prompt_id} 执行完成。")
                                        prompt_done = True
                                        break # 我们的 prompt 执行完毕
                                    else:
                                        pass

                            elif msg_type == "executed":
                                if data.get("prompt_id") == prompt_id:
                                    node_id = data.get("node")
                                    outputs = data.get("output", {}).get("images", [])
                                    print(f"Prompt {prompt_id} 节点 {node_id} 执行完毕。输出图片数量: {len(outputs)}")
                                    for img_detail in outputs:
                                        output_images_details.append(img_detail)
                                        print(f"  找到图片: {img_detail.get('filename')}")

                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print(f"WebSocket 连接错误: {ws.exception()}")
                        break
                    elif msg.type == aiohttp.WSMsgType.CLOSED:
                        print("WebSocket 连接已关闭。")
                        break

        history = await self.get_history(prompt_id)
        if history and prompt_id in history:
            final_images_to_fetch = []
            prompt_outputs = history[prompt_id].get("outputs", {})

            for node_id, node_output in prompt_outputs.items():
                #print(node_output)
                if "images" in node_output:
                    for img_info in node_output["images"]:
                        print(f"从历史记录中找到图片: 节点 {node_id}, 文件名 {img_info.get('filename')}")
                        if img_info not in final_images_to_fetch: # 避免重复
                            final_images_to_fetch.append(img_info)
        
                    for img_detail in final_images_to_fetch:
                        img_data = await self.get_image(
                            img_detail["filename"],
                            img_detail.get("subfolder", ""), # subfolder 可能不存在
                            img_detail["type"]
                        )
                        if img_data:
                            file_path = os.path.join(self.OUTPUT_IMAGE_FILE_PATH, img_detail["filename"])
                            with open(file_path, "wb") as f:
                                f.write(img_data)
                            print(f"图片已保存到: {file_path}")
                            #目前只处理第一张
                            return file_path
