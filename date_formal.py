import xml.etree.ElementTree as ET
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import math, re, os

class PlotlyVisualizer:
    def __init__(self, folder_path, time_range = "2020-01-01"):
        self.folder_path = folder_path
        self.time_range = time_range

    # 从 xml 文件名获取用户名 username 与导出时间 export_time
    # acquire username and export_time from the xml file  
    def extract_info_from_filename(self, filename):
        pattern = r'vndb-list-export-(\w+)-(\d{14}).xml'
        match = re.match(pattern, filename)
        if match:
            username = match.group(1)
            export_time_str = match.group(2)
            export_time = datetime.strptime(export_time_str, '%Y%m%d%H%M%S')
            return username, export_time
        else:
            raise ValueError(f"xml文件名格式不匹配: {filename}")

    # 确定最新的 xml 文件
    # identify the latest xml file
    def process_files(self):
        file_list = os.listdir(self.folder_path)

        latest_file = None
        latest_export_time = datetime(1970, 1, 1)
        usernames = set()

        for filename in file_list:
            if filename.endswith('.xml'):
                username, export_time = self.extract_info_from_filename(filename)
                usernames.add(username)
                if export_time > latest_export_time:
                    latest_export_time = export_time
                    latest_file = filename
        if latest_file is None:
            raise ValueError("没有找到匹配的xml文件")
        if len(usernames) > 1:
            raise ValueError("存在多个用户")

        return latest_file

    # 解析 xml 文件，返回作品信息
    # resolve the xml file and return VNs information
    def extract_vn_info(self):
        vns = ET.parse(self.process_files()).getroot().find('vns')
        results = [] # 创建空列表用于储存结果
        for vn in vns.findall('vn'):

            #提取开始日期
            try:
                started = vn.find('started').text
                if datetime.strptime(started, "%Y-%m-%d") < datetime.strptime(self.time_range, "%Y-%m-%d"):
                    continue
            except:
                continue # 无开始日期直接跳过

            # 提取标题
            title = vn.find('title').get('original')
            if title == None:
                title = vn.find('title').text #原名即为罗马字母时无 original项

            #提取标签
            try:
                label = vn.find('label').get('label')
            except:
                label = "Finished"

            # 提取结束日期 
            try:
                finished = vn.find('finished').text
            except:
                # 尚无结束日期的搁置作品，按迄今天数之对数确定显示长度
                if label == 'Stalled':
                    days_diff = (pd.to_datetime(datetime.today().date())-pd.to_datetime(started)).days
                    line_length = math.log(days_diff+1, 1.27) # 带有一定经验性的对数之底
                    finished = pd.to_datetime(started) + pd.DateOffset(days=line_length)
                else:
                    finished = pd.to_datetime(datetime.today().date())

            results.append(dict({'title': title, 'started': started, 'finished': finished,  'label': label}))
        return results

    # 结果可视化
    # visualization
    def visualize_data(self):
        results = self.extract_vn_info()
        df = pd.DataFrame(results)

        # 标签-颜色映射表
        color_mapping = {
            'Finished': '#377eb8',
            'Dropped': '#b30000',
            'Stalled': 'rgba(184, 0, 230, 0.3)', # '#b800e6'
            'Playing': '#00ffff',
            'Wishlist': '#ffff99'
        }

        # 图片生成
        fig = px.timeline(df, x_start='started', x_end='finished', y='title', color='label', color_discrete_map=color_mapping)

        # 起迄时间控制
        fig.update_xaxes(range=[
            self.time_range, datetime.today().date()
        ])

        # 生成图片后再按 started 排序，否则会按颜色映射分组、每组内再按 started 排序
        sorted_df = df[['started', 'title']].sort_values(by='started')
        sorted_title_list = sorted_df['title'].tolist()
        fig.update_yaxes(categoryorder='array', categoryarray=sorted_title_list)#, autorange='reversed')

        # 根据项目数调整高度，设置背景颜色；设置标题
        username, export_time = self.extract_info_from_filename(self.process_files())
        fig.update_layout(
            height = len(results) * 30, #经验性的高度
            plot_bgcolor = '#e5f0ff',
            title_text = f"vndb用户{username}的视觉小说可视化，<br>数据导出时间：{export_time}",
        )

        for index, row in df.iterrows():
            # 对于起止日期相同的作品，直接标注日期
            if row['started'] == row['finished']:
                fig.add_annotation(
                    text=row['started'][-5:],
                    x=row['started'],
                    y=row['title'],
                    showarrow=False,
                    xshift=-3,  # 控制水平偏移
                    font=dict(size=10),  # 设置字体大小
                    align='right',  # 文本对齐方式
                    valign='middle',  # 文本对齐方式
                    hovertext=f"label: {row['label']}<br>started: {datetime.strptime(row['started'], '%Y-%m-%d').strftime('%b %d, %Y')}<br>finished: {datetime.strptime(row['finished'], '%Y-%m-%d').strftime('%b %d, %Y')}<br>title:{row['title']}", # 试图自动将 annotation 的悬浮文本与正常 finished 内容统一，目前只能手动
                    hoverlabel=dict(
                        bgcolor='#377eb8',  # 设置悬浮文本的背景颜色
                        font=dict(
                            family='Arial',  # 设置悬浮文本的字体
                            size=13,  # 设置悬浮文本的字体大小
                            color='white',  # 设置悬浮文本的字体颜色
                        )
                    )
                )
        
        fig.show()

if __name__ == '__main__':
    folder_path = os.path.dirname(os.path.abspath(__file__))
    Visualizer = PlotlyVisualizer(folder_path, "2020-01-01")
    Visualizer.visualize_data()