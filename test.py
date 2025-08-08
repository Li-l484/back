import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle
import re
import math
from matplotlib.transforms import Affine2D
import matplotlib.patches as mpatches
import check

# 设置支持中文的字体
plt.rcParams["font.family"] = ["Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False


def parse_points(points_list):
    """解析坐标点列表，提取X和Y坐标"""
    coordinates = []
    pattern = r'X=([\-\d.]+)\s+Y=([\-\d.]+)\s+Z=([\-\d.]+)'

    for point in points_list:
        match = re.match(pattern, point)
        if match:
            x = float(match.group(1))
            y = -float(match.group(2))
            coordinates.append((x, y))

    return coordinates


def parse_location(location_str):
    """解析location字符串，返回X和Y坐标"""
    pattern = r'X=([\-\d.]+)\s+Y=([\-\d.]+)\s+Z=([\-\d.]+)'
    match = re.match(pattern, location_str)
    if match:
        x = float(match.group(1))
        y = -float(match.group(2))
        return (x, y)
    return (0, 0)


def parse_rotation(rotation_str):
    """解析rotation字符串，返回Y轴旋转角度（度）"""
    pattern = r'P=([\-\d.]+)\s+Y=([\-\d.]+)\s+R=([\-\d.]+)'
    match = re.match(pattern, rotation_str)
    if match:
        return float(match.group(2))  # 取Y轴旋转角度
    return 0.0


def calculate_distance(p1, p2):
    """计算两点之间的欧氏距离"""
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def draw_furniture(ax, x, y, length, width, angle, color, name, unit_scale=1.0):
    """
    绘制带旋转角度的家具/设备矩形
    length: 长度（原始单位）
    width: 宽度（原始单位）
    angle: 旋转角度（度）
    unit_scale: 单位换算比例（如毫米转厘米为0.1）
    """
    # 应用单位换算
    scaled_length = length * unit_scale
    scaled_width = width * unit_scale

    # 创建矩形，以中心为原点
    rect = Rectangle((-scaled_length / 2, -scaled_width / 2), scaled_length, scaled_width,
                     facecolor=color, edgecolor='black',
                     linewidth=1.5, alpha=0.8)

    # 应用旋转和平移变换
    transform = Affine2D().rotate_deg(angle).translate(x, y) + ax.transData
    rect.set_transform(transform)

    # 添加矩形到坐标轴
    ax.add_patch(rect)


def get_device_corners(x, y, length, width, angle, unit_scale=1.0):
    """
    获取设备矩形的四个角点坐标
    返回: [(x1,y1), (x2,y2), (x3,y3), (x4,y4)] 按顺时针顺序
    """
    scaled_length = length * unit_scale
    scaled_width = width * unit_scale

    # 矩形的四个角点（以中心为原点）
    corners = [
        (-scaled_length / 2, -scaled_width / 2),  # 左下
        (scaled_length / 2, -scaled_width / 2),  # 右下
        (scaled_length / 2, scaled_width / 2),  # 右上
        (-scaled_length / 2, scaled_width / 2)  # 左上
    ]

    # 应用旋转和平移变换
    cos_a = math.cos(math.radians(angle))
    sin_a = math.sin(math.radians(angle))

    transformed_corners = []
    for cx, cy in corners:
        # 旋转
        rx = cx * cos_a - cy * sin_a
        ry = cx * sin_a + cy * cos_a
        # 平移
        tx = rx + x
        ty = ry + y
        transformed_corners.append((tx, ty))

    return transformed_corners


def get_device_edges(corners):
    """
    获取设备矩形的四条边
    返回: [(start_point, end_point, direction), ...]
    direction: 'up', 'down', 'left', 'right' 表示边的方向
    """
    edges = []
    directions = ['right', 'up', 'left', 'down']  # 对应四条边的方向

    for i in range(4):
        start = corners[i]
        end = corners[(i + 1) % 4]
        direction = directions[i]
        edges.append((start, end, direction))

    return edges


def get_edge_midpoint(start, end):
    """获取边的中点"""
    return ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)


def point_to_line_distance(point, line_start, line_end):
    """计算点到线段的距离"""
    x0, y0 = point
    x1, y1 = line_start
    x2, y2 = line_end

    # 线段长度
    line_length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    if line_length == 0:
        return math.sqrt((x0 - x1) ** 2 + (y0 - y1) ** 2)

    # 计算投影点参数 t
    t = max(0, min(1, ((x0 - x1) * (x2 - x1) + (y0 - y1) * (y2 - y1)) / (line_length ** 2)))

    # 投影点坐标
    proj_x = x1 + t * (x2 - x1)
    proj_y = y1 + t * (y2 - y1)

    # 点到投影点的距离
    return math.sqrt((x0 - proj_x) ** 2 + (y0 - proj_y) ** 2)


def find_nearest_room_edge(midpoint, direction, room_coordinates):
    """在指定方向上找到最近的房间边"""
    min_distance = float('inf')
    nearest_edge = None

    for room_coords in room_coordinates:
        num_points = len(room_coords)
        for i in range(num_points):
            edge_start = room_coords[i]
            edge_end = room_coords[(i + 1) % num_points]

            # 检查边的方向是否与目标方向一致
            edge_direction = get_edge_direction(edge_start, edge_end)
            if is_direction_compatible(direction, edge_direction):
                # 计算距离时考虑方向
                if direction == 'right' and edge_start[0] > midpoint[0]:
                    distance = point_to_line_distance(midpoint, edge_start, edge_end)
                elif direction == 'left' and edge_start[0] < midpoint[0]:
                    distance = point_to_line_distance(midpoint, edge_start, edge_end)
                elif direction == 'up' and edge_start[1] > midpoint[1]:
                    distance = point_to_line_distance(midpoint, edge_start, edge_end)
                elif direction == 'down' and edge_start[1] < midpoint[1]:
                    distance = point_to_line_distance(midpoint, edge_start, edge_end)
                else:
                    continue

                if distance < min_distance:
                    min_distance = distance
                    nearest_edge = (edge_start, edge_end)

    return nearest_edge, min_distance


def get_edge_direction(start, end):
    """获取边的方向"""
    dx = end[0] - start[0]
    dy = end[1] - start[1]

    if abs(dx) > abs(dy):
        return 'horizontal'
    else:
        return 'vertical'


def is_direction_compatible(target_dir, edge_dir):
    """检查目标方向是否与边方向兼容"""
    if target_dir in ['left', 'right']:
        return edge_dir == 'horizontal'
    elif target_dir in ['up', 'down']:
        return edge_dir == 'vertical'
    return False


def calculate_ray_intersection(midpoint, direction, room_coordinates):
    """计算射线与房间轮廓的首次交点"""
    x0, y0 = midpoint
    min_distance = float('inf')
    intersection_point = None

    for room_coords in room_coordinates:
        num_points = len(room_coords)
        for i in range(num_points):
            edge_start = room_coords[i]
            edge_end = room_coords[(i + 1) % num_points]

            # 计算射线与边的交点
            inter = calculate_line_intersection(midpoint, direction, edge_start, edge_end)
            if inter:
                ix, iy = inter
                distance = math.hypot(ix - x0, iy - y0)

                if distance < min_distance:
                    min_distance = distance
                    intersection_point = inter

    return intersection_point, min_distance


def calculate_line_intersection(midpoint, direction, edge_start, edge_end):
    """计算射线与线段的交点"""
    x0, y0 = midpoint
    x1, y1 = edge_start
    x2, y2 = edge_end

    # 根据方向设置射线的方向向量
    if direction == 'right':
        dx, dy = 1, 0
    elif direction == 'left':
        dx, dy = -1, 0
    elif direction == 'up':
        dx, dy = 0, 1
    elif direction == 'down':
        dx, dy = 0, -1

    # 计算交点
    denominator = (x2 - x1) * dy - (y2 - y1) * dx
    if denominator == 0:
        return None  # 平行，无交点

    t = ((x0 - x1) * dy - (y0 - y1) * dx) / denominator
    u = ((x0 - x1) * (y2 - y1) - (y0 - y1) * (x2 - x1)) / denominator

    if 0 <= t <= 1 and u >= 0:
        # 交点在边上且在射线上
        ix = x1 + t * (x2 - x1)
        iy = y1 + t * (y2 - y1)
        return (ix, iy)

    return None


def calculate_device_to_room_distances(device_info, room_coordinates, unit_scale=1.0):
    """
    计算设备各边到房间轮廓边的距离
    返回: {edge_direction: distance}
    """
    x, y = parse_location(device_info.get('location', ''))
    angle = parse_rotation(device_info.get('rotation', ''))
    length = float(device_info.get('length', 600))
    width = float(device_info.get('width', 300))

    # 获取设备角点和边
    corners = get_device_corners(x, y, length, width, angle, unit_scale)
    edges = get_device_edges(corners)

    distances = {}

    for start, end, direction in edges:
        midpoint = get_edge_midpoint(start, end)
        intersection, distance = calculate_ray_intersection(midpoint, direction, room_coordinates)

        if intersection:
            distances[direction] = distance

    return distances


def calculate_ray_intersection_from_center(midpoint, center, room_coordinates):
    """
    从边中点出发，沿远离中心的方向作射线，计算与房间轮廓的首次交点和距离
    """
    x0, y0 = midpoint
    cx, cy = center
    dx = x0 - cx
    dy = y0 - cy
    norm = math.hypot(dx, dy)
    if norm == 0:
        return None, float('inf')
    dx /= norm
    dy /= norm

    min_distance = float('inf')
    intersection_point = None

    for room_coords in room_coordinates:
        num_points = len(room_coords)
        for i in range(num_points):
            x1, y1 = room_coords[i]
            x2, y2 = room_coords[(i + 1) % num_points]

            # 射线参数方程: (x, y) = (x0, y0) + t*(dx, dy)
            # 线段参数方程: (x, y) = (x1, y1) + s*((x2-x1), (y2-y1)), 0<=s<=1
            denom = (dx * (y1 - y2) - dy * (x1 - x2))
            if abs(denom) < 1e-8:
                continue  # 平行
            t = ((x1 - x0) * (y1 - y2) - (y1 - y0) * (x1 - x2)) / denom
            s = ((x0 - x1) * dy - (y0 - y1) * dx) / ((x2 - x1) * dy - (y2 - y1) * dx + 1e-12)
            if t > 0 and 0 <= s <= 1:
                ix = x0 + t * dx
                iy = y0 + t * dy
                distance = math.hypot(ix - x0, iy - y0)
                if distance < min_distance:
                    min_distance = distance
                    intersection_point = (ix, iy)
    return intersection_point, min_distance


def draw_distance_lines(ax, device_info, room_coordinates, unit_scale=1.0):
    """绘制设备边到房间边的距离线（修正版）"""
    # 检查是参数化模型还是硬件设备
    # 参数化模型的特征：有name字段且包含特定关键词，或者来自NewWHCMode
    is_parametric = (
            'name' in device_info and
            ('电视柜' in device_info.get('name', '') or 'Y4060' in device_info.get('name', ''))
    )

    if is_parametric:
        # 参数化模型
        x, y = parse_location(device_info.get('location', ''))
        angle = parse_rotation(device_info.get('rotation', ''))
    else:
        # 硬件设备
        x, y = parse_location(device_info.get('location', ''))
        angle = parse_rotation(device_info.get('rotation', ''))

    length = float(device_info.get('length', 600))
    width = float(device_info.get('width', 300))

    # 检查位置是否有效
    if (x, y) == (0, 0):
        return

    # 对于参数化模型，需要计算中心点
    if is_parametric:
        # 参数化模型从端点开始，需要计算中心点
        scaled_length = length * unit_scale
        scaled_width = width * unit_scale

        draw_angle = (270 - angle) % 360

        # 计算中心点（从端点向模型内部偏移半长度）
        cos_a = math.cos(math.radians(draw_angle))
        sin_a = math.sin(math.radians(draw_angle))
        center_x = x + (scaled_length / 2) * cos_a
        center_y = y + (scaled_length / 2) * sin_a

        print(f"    参数化模型端点: ({x:.1f}, {y:.1f})")
        print(f"    参数化模型中心: ({center_x:.1f}, {center_y:.1f})")

        # 使用中心点进行距离计算
        x, y = center_x, center_y

    # 获取设备角点和边
    corners = get_device_corners(x, y, length, width, angle, unit_scale)
    edges = get_device_edges(corners)

    # 只从模型中心计算距离，不重复计算
    for start, end, direction in edges:
        midpoint = get_edge_midpoint(start, end)
        intersection, distance = calculate_ray_intersection_from_center(midpoint, (x, y), room_coordinates)
        if intersection:
            ix, iy = intersection
            ax.plot([midpoint[0], ix], [midpoint[1], iy],
                    'r--', linewidth=1, alpha=0.7)
            ax.text((midpoint[0] + ix) / 2, (midpoint[1] + iy) / 2,
                    f'{distance:.1f}cm', ha='center', va='center',
                    fontsize=8, color='red', bbox=dict(facecolor='white', alpha=0.8))


def calculate_intersection(midpoint, direction, edge_start, edge_end):
    """计算设备边中点与房间边的交点"""
    if direction in ['left', 'right']:
        # 水平边，计算垂直交点
        return (midpoint[0], edge_start[1])
    else:
        # 垂直边，计算水平交点
        return (edge_start[0], midpoint[1])


def parse_location_for_parametric(location_str):
    """为参数化模型解析location字符串，Y轴向下为正"""
    pattern = r'X=([\-\d.]+)\s+Y=([\-\d.]+)\s+Z=([\-\d.]+)'
    match = re.match(pattern, location_str)
    if match:
        x = float(match.group(1))
        y = -float(match.group(2))  # 取负值，使Y轴向下为正
        return (x, y)
    return (0, 0)


def parse_rotation_for_parametric(rotation_str):
    """为参数化模型解析rotation字符串"""
    pattern = r'P=([\-\d.]+)\s+Y=([\-\d.]+)\s+R=([\-\d.]+)'
    match = re.match(pattern, rotation_str)
    if match:
        return float(match.group(2))  # 取Y轴旋转角度
    return 0.0


# def draw_parametric_furniture(ax, start_x, start_y, length, width, angle, color, name, unit_scale=1.0, scale_x=1.0 , scale_y=1.0):
#     """
#     绘制参数化模型，以指定点为端点起始点，根据rotation中的Y值决定绘制方向
#     start_x, start_y: 端点起始点坐标
#     length, width: 模型的长和宽（毫米）
#     angle: 旋转角度（度）
#     """
#     # 应用单位换算
#     scaled_length = length * unit_scale
#     scaled_width = width * unit_scale
#
#     draw_angle = (270 - angle) % 360
#
#     # 如果X方向翻转，调整角度
#     if scale_x < 0:
#         draw_angle = (draw_angle + 180) % 180
#     # 如果Y方向翻转，也需要调整角度
#     if scale_y < 0:
#         draw_angle = (draw_angle + 180) % 180
#     # 直接以端点作为矩形的起始点，创建矩形
#     rect = Rectangle((0, 0), scaled_length, scaled_width,
#                      facecolor=color, edgecolor='black',
#                      linewidth=1.5, alpha=0.8)
#
#     # 应用旋转和平移变换
#     transform = Affine2D().rotate_deg(draw_angle).translate(start_x, start_y) + ax.transData
#     rect.set_transform(transform)
#
#     # 添加矩形到坐标轴
#     ax.add_patch(rect)
#
#     return start_x, start_y
def draw_parametric_furniture(ax, start_x, start_y, length, width, angle, color, name, unit_scale=1.0, scale_x=1.0,
                              scale_y=1.0):
    """
    绘制参数化模型，支持沿X/Y轴翻转
    - scale_x < 0: 沿Y轴翻转（左右镜像）
    - scale_y < 0: 沿X轴翻转（上下镜像）
    """
    # 应用单位换算
    scaled_length = abs(length) * unit_scale
    scaled_width = abs(width) * unit_scale

    # 基础旋转角度（原始逻辑保持）
    draw_angle = (270 - angle) % 360

    # 处理沿Y轴翻转（scale_x < 0）：左右镜像
    if scale_x < 0:
        # 沿Y轴翻转需要将旋转角度反向180度，并调整起始点偏移
        draw_angle = (draw_angle + 180) % 360
        # 计算长度方向的偏移量（翻转后起始点沿长度方向反向移动）
        offset_x = scaled_length * np.cos(np.radians(draw_angle))
        offset_y = scaled_length * np.sin(np.radians(draw_angle))
        start_x -= offset_x
        start_y -= offset_y

    # 处理沿X轴翻转（scale_y < 0）：上下镜像
    if scale_y < 0:
        # 沿X轴翻转需要将旋转角度反向180度，并调整起始点偏移
        draw_angle = (draw_angle + 180) % 360
        # 计算宽度方向的偏移量（翻转后起始点沿宽度方向反向移动）
        offset_x = scaled_width * np.cos(np.radians(draw_angle + 90))  # +90度是宽度方向的垂直角度
        offset_y = scaled_width * np.sin(np.radians(draw_angle + 90))
        start_x -= offset_x
        start_y -= offset_y

    # 创建矩形（尺寸用绝对值保证正确）
    rect = Rectangle((0, 0), scaled_length, scaled_width,
                     facecolor=color, edgecolor='black',
                     linewidth=1.5, alpha=0.8)

    # 应用旋转和平移变换
    transform = Affine2D().rotate_deg(draw_angle).translate(start_x, start_y) + ax.transData
    rect.set_transform(transform)

    ax.add_patch(rect)
    return start_x, start_y


def plot_room_with_furniture():
    """绘制房间轮廓、边长及按实际尺寸的软装"""
    fig, ax = plt.subplots(figsize=(14, 12))
    room_colors = ['#FFA07A', '#98FB98', '#87CEFA', '#DDA0DD', '#F0E68C']

    # 单位换算比例：设备尺寸（毫米）转房间坐标单位（假设为厘米）
    # 1厘米 = 10毫米 → 比例为0.1
    unit_scale = 0.1

    # 收集所有房间坐标用于距离计算
    all_room_coordinates = []

    # 绘制房间轮廓和边长
    for i, room in enumerate(check.get_roomList()):
        room_id = room['SpaceId']
        room_name = room['Name']
        points = room['points']
        coordinates = parse_points(points)

        if not coordinates:
            print(f"房间 {room_name} (ID: {room_id}) 没有有效的坐标点")
            continue

        all_room_coordinates.append(coordinates)

        # 绘制房间多边形
        polygon = Polygon(
            coordinates,
            fill=True,
            alpha=0.5,
            color=room_colors[i % len(room_colors)],
            edgecolor='black',
            linewidth=2,
            label=f"{room_name} (ID: {room_id})"
        )
        ax.add_patch(polygon)

        # 标注房间名称
        centroid_x = sum(p[0] for p in coordinates) / len(coordinates)
        centroid_y = sum(p[1] for p in coordinates) / len(coordinates)
        plt.text(
            centroid_x, centroid_y,
            room_name,
            ha='center', va='center',
            fontweight='bold',
            fontsize=10,
            bbox=dict(facecolor='white', edgecolor='gray', pad=3, boxstyle='round,pad=0.5')
        )

    # # 绘制普通插座（hydropowerMode）
    for item in check.get_hydropowerModeList():
        if not item:
            continue

        loc = parse_location(item.get('location', ''))
        rot = parse_rotation(item.get('rotation', ''))
        # 插座原始尺寸（毫米）
        length = float(item.get('length', 100))  # 实际插座约100mm
        width = float(item.get('width', 100))
        name = item.get('pointUse', '插座')

        # 绘制时应用单位换算
        draw_furniture(ax, loc[0], loc[1], length, width, rot, 'blue', name, unit_scale)

    # 绘制硬件设备（hardMode）
    for item in check.get_hardModeList():
        if not item:
            continue

        loc = parse_location(item.get('location', ''))
        rot = parse_rotation(item.get('rotation', ''))
        # 设备原始尺寸（毫米）
        length = float(item.get('length', 600))
        width = float(item.get('width', 300))
        name_str = item.get('name') or item.get('pointUse') or '设备'
        name = name_str.split('-')[0]

        # 绘制时应用单位换算
        draw_furniture(ax, loc[0], loc[1], length, width, rot, 'pink', name, unit_scale)

        # 绘制设备到房间边的距离线
        # draw_distance_lines(ax, item, all_room_coordinates, unit_scale)

    # 绘制参数化模型（NewWHCMode）
    for item in check.get_NewWHCModeList():
        if not item:
            continue

        # # 参数化模型使用专门的解析函数，Y轴向下为正
        original_loc = parse_location_for_parametric(item.get('location', ''))
        rot = parse_rotation_for_parametric(item.get('rotation', ''))

        # 解析scale值
        scale_str = item.get('scale', 'X=1.000 Y=1.000 Z=1.000')
        scale_x = float(scale_str.split('X=')[1].split()[0])
        scale_y = float(scale_str.split('Y=')[1].split()[0])

        # 从 ParameterList 中获取尺寸信息
        length = float(item.get('length', 600))
        width = float(item.get('width', 300))
        name_str = item.get('name') or '设备'
        name = name_str.split('-')[0]

        # 直接使用原始位置
        loc = original_loc

        # 绘制时应用单位换算
        draw_parametric_furniture(ax, loc[0], loc[1], length, width, rot, 'lightblue', name, unit_scale, scale_x,
                                  scale_y)

        # # 绘制设备到房间边的距离线
        # draw_distance_lines(ax, item, all_room_coordinates, unit_scale)
    # 添加图例
    # room_patch = mpatches.Patch(color=room_colors[0], alpha=0.5, label='房间（单位：cm）')
    socket_patch = mpatches.Patch(color='blue', alpha=0.8, label='插座（单位：cm）')
    device_patch = mpatches.Patch(color='pink', alpha=0.8, label='非参数化模型（单位：cm）')
    NewWHCMode_patch = mpatches.Patch(color='lightblue', alpha=0.8, label='参数化模型（单位：cm）')
    # distance_patch = mpatches.Patch(color='red', alpha=0.7, label='设备到房间边距离')
    ax.legend(handles=[socket_patch, device_patch, NewWHCMode_patch], loc='upper right')

    # 设置图表属性
    plt.axis('equal')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.title('房间轮廓与软装布局图（含距离标注）', fontsize=14)
    plt.xlabel('X坐标（cm）', fontsize=12)
    plt.ylabel('Y坐标（cm）', fontsize=12)

    # 调整坐标轴范围
    all_points = [p for room in check.get_roomList() for p in parse_points(room['points'])]
    all_points += [parse_location(item.get('location', '')) for item in check.get_hydropowerModeList() if item]
    all_points += [parse_location(item.get('location', '')) for item in check.get_hardModeList() if item]

    if all_points:
        all_x = [p[0] for p in all_points]
        all_y = [p[1] for p in all_points]
        max_size = max(
            [float(item.get('length', 0)) * unit_scale for item in check.get_hydropowerModeList() if item] +
            [float(item.get('width', 0)) * unit_scale for item in check.get_hydropowerModeList() if item] +
            [float(item.get('length', 0)) * unit_scale for item in check.get_hardModeList() if item] +
            [float(item.get('width', 0)) * unit_scale for item in check.get_hardModeList() if item] +
            [50]
        )
        plt.xlim(min(all_x) - max_size, max(all_x) + max_size)
        plt.ylim(min(all_y) - max_size, max(all_y) + max_size)

    plt.tight_layout()
    image_path = 'floorplan.png'
    plt.savefig(image_path)
    plt.show()
    plt.close(fig)
    return image_path