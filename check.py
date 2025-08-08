import json
import requests
from flask import request


def parse_scale(scale_str):
    """解析scale字符串为字典，格式如"X=1 Y=1 Z=1" """
    scale = {'X': 1.0, 'Y': 1.0, 'Z': 1.0}  # 默认缩放比例
    if not scale_str:
        return scale

    try:
        scale_parts = scale_str.split()
        for part in scale_parts:
            key, value = part.split('=')
            if key in scale:
                scale[key] = float(value)
    except Exception as e:
        print(f"解析scale出错: {e}, scale_str={scale_str}")

    return scale

def get_bim_json():
    try:
        data = request.get_json()
        Bimjson_URL = data.get('url')
        response = requests.get(f"{Bimjson_URL}")
        bimjson = response.json()
        if bimjson is not None:
            return bimjson
        else:
            print("data为空")
    except Exception as e:
        print(f"获取BimJson失败: {e}")
        return None

def get_roomList():
    roomList = get_bim_json().get("layoutMode", {}).get("roomList", [])
    Room = []
    for room in roomList:
        Room.append({
            "SpaceId" : room.get("SpaceId"),
            "Name": room.get("Name"),
            "points": room.get("points")
        })
    with open('Room.json', 'w', encoding='utf-8') as file:
        json.dump(Room, file, ensure_ascii=False, indent=2)
    return Room

def get_hardModeList():
    hardModeList = get_bim_json().get("hardMode", {}).get("moveableMeshList", [])
    hardMode = []
    # 提取所有有效的id
    hard_ids = [item.get("id") for item in hardModeList]
    # 获取模型数据
    model_data = get_model(hard_ids) or []

    model_dict = {}

    # 将模型数据转为以id为键的字典，方便查找
    for model in model_data:
        if model and isinstance(model, dict) and "id" in model:
            model_id = str(model["id"])
            model_dict[model_id] = model
    for hard in hardModeList:
            scale = parse_scale(hard.get('scale'))
            hard_info = {
                "id": hard.get('id'),
                "location": hard.get('location'),
                "rotation": hard.get('rotation'),
                "scale": hard.get('scale')
            }
            # 查找对应的模型尺寸信息
            model = model_dict.get(str(hard.get('id')))
            if model:
                classify_name = model.get("classifyName")
                if classify_name not in ["婴儿床", "双人床", "高低_子母床", "单人床", "沙发床", "三人沙发", "餐桌", "餐椅", "淋浴房", "双人沙发", "多人沙发", "茶几" ]:
                    continue
                length = model.get("length", 0) * scale['X']
                width = model.get("width", 0) * scale['Y']
                height = model.get("height", 0) * scale['Z']
                hard_info.update({
                    "name": model.get("name"),
                    "length": length,
                    "width": width,
                    "height": height,
                    "sysObjName": model.get("sysObjName")
                })

            hardMode.append(hard_info)

    with open('hardMode.json', 'w', encoding='utf-8') as file:
        json.dump(hardMode, file, ensure_ascii=False, indent=2)
    return hardMode

def get_hydropowerModeList():
    hydropowerModeList = get_bim_json().get("hydropowerMode", {}).get("moveableMeshList", [])
    hydropowerMode = []

    # 提取所有有效的id
    hydropower_ids = [item.get("id") for item in hydropowerModeList
                      if item.get("id") and item.get("pointUse") is not None]

    # 获取模型数据
    model_data = get_model(hydropower_ids) or []

    model_dict = {}
    # 将模型数据转为以id为键的字典，方便查找
    for model in model_data:
        if model and isinstance(model, dict) and "id" in model:
            model_id = str(model["id"])
            model_dict[model_id] = model

    for hydropower in hydropowerModeList:
        hydropower_id = hydropower.get("id")
        if hydropower_id and hydropower.get("pointUse") is not None:
            scale = parse_scale(hydropower.get('scale'))
            hydropower_info = {
                "id": hydropower_id,
                "pointUse": hydropower.get('pointUse'),
                "location": hydropower.get('location'),
                "rotation": hydropower.get('rotation'),
                "scale": hydropower.get('scale')
            }
            # 查找对应的模型尺寸信息
            model = model_dict.get(str(hydropower_id))
            if model:
                length = model.get("length", 0) * scale['X']
                width = model.get("width", 0) * scale['Y']
                height = model.get("height", 0) * scale['Z']
                hydropower_info.update({
                    "length": length,
                    "width": width,
                    "height": height,
                    "sysObjName": model.get("sysObjName")
                })
            else:
                print(f"未找到匹配模型: hydropower_id={hydropower_id}")  # 调试日志

            hydropowerMode.append(hydropower_info)

    with open('hydropowerMode.json', 'w', encoding='utf-8') as file:
        json.dump(hydropowerMode, file, ensure_ascii=False, indent=2)
    return hydropowerMode

def get_NewWHCModeList():
    NewWHCModeList = get_bim_json().get("NewWHCMode", {}).get("cab_data_list", [])
    NewWHCMode = []

    # 提取所有有效的id
    NewWHCMode_ids = [item.get("ContentItemID") for item in NewWHCModeList
                      if item.get("ContentItemID") is not None]

    # 获取模型数据
    model_data = get_model(NewWHCMode_ids) or []

    model_dict = {}
    # 将模型数据转为以id为键的字典，方便查找
    for model in model_data:
        if model and isinstance(model, dict) and "id" in model:
            model_id = str(model["id"])
            model_dict[model_id] = model

    for NewWHCM in NewWHCModeList:
        NewWHC_id = NewWHCM.get("ContentItemID")
        if NewWHC_id is not None:
            # 初始化基础信息
            NewWHCMode_info = {
                "id": NewWHC_id,
                "name": NewWHCM.get("name"),
                "location": NewWHCM.get('Pos'),
                "rotation": NewWHCM.get('Rotation'),
                "scale": NewWHCM.get('Scale')
            }

            # 提取ParameterList中的宽度、深度、高度
            param_list = NewWHCM.get("ParameterList", [])
            for param in param_list:
                param_name = param.get("ParamName")
                param_value = param.get("Value")
                # 根据参数名匹配并添加到结果中
                if param_name == "深度":
                    NewWHCMode_info["length"] = param_value
                elif param_name == "宽度":
                    NewWHCMode_info["width"] = param_value
                elif param_name == "高度":
                    NewWHCMode_info["height"] = param_value

            # 查找对应的模型尺寸信息（如果需要保留模型数据中的尺寸）
            model_key = str(NewWHC_id)
            model = model_dict.get(model_key)
            if model:
                # classify_name = model.get("classifyName")
                # if classify_name not in ["电视柜", "掩门衣柜"]:
                #     continue
                # 这里可以选择保留模型中的其他信息
                NewWHCMode_info.update({
                    "sysObjName": model.get("sysObjName"),
                    "classifyName": model.get("classifyName")
                })
            else:
                print(f"未找到匹配模型: {model_key} (字典中存在的键: {model_key in model_dict})")

            NewWHCMode.append(NewWHCMode_info)

    with open('NewWHCMode.json', 'w', encoding='utf-8') as file:
        json.dump(NewWHCMode, file, ensure_ascii=False, indent=2)
    return NewWHCMode

def get_model(id_list, default_ids=[974123]):
    model_URL = "http://i.bim-zeus.home.ke.com/api/resGoods/pcLoadPlanGoodsList"
    try:
        body = id_list if id_list else default_ids
        response = requests.post(model_URL, json=body)

        response_json = response.json()

        # 检查响应状态
        if response_json.get("success") and response_json.get("code") == 2000:
            model = response_json.get("data", [])
            return model
        else:
            return []
    except Exception as e:
        print(f"请求模型链接失败: {e}")
        return []
