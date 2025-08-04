#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Oracle数据库读取URL，解析ID并下载PDF文件
"""

import os
import re
import json
import requests
import cx_Oracle
from urllib.parse import urlparse, parse_qs
import time
from datetime import datetime
from urllib.parse import quote

class PDFDownloader:
    def __init__(self, db_config):
        """
        初始化PDF下载器

        Args:
            db_config (dict): 数据库配置信息
        """
        self.db_config = db_config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Content-Type': 'application/json'
        })

    def connect_oracle(self):
        """连接Oracle数据库"""
        try:
            connection_str = f"{self.db_config['username']}/{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['service_name']}"
            connection = cx_Oracle.connect(connection_str)
            print(f"✅ 成功连接到Oracle数据库")
            return connection
        except Exception as e:
            print(f"❌ 连接Oracle数据库失败: {str(e)}")
            return None

    def get_urls_from_db(self):
        """从数据库获取URL列表"""
        connection = self.connect_oracle()
        if not connection:
            return []

        try:
            cursor = connection.cursor()
            # 使用您提供的SQL查询
            sql = """
            select REGEXP_SUBSTR(content, '(.*)公示源URL[:：](.*?)公示类型', 1, 1, 'i', 2) as winner_category 
            from zjw_jyzx_data 
            where CATEGORY_NAME='中标候选人公示'
            and REGEXP_SUBSTR(content, '(.*)公示源URL[:：](.*?)公示类型', 1, 1, 'i', 2) is not null
            """

            cursor.execute(sql)
            urls = []
            for row in cursor:
                url = row[0]
                if url and url.strip():
                    urls.append(url.strip())

            print(f"📋 从数据库获取到 {len(urls)} 个URL")
            return urls

        except Exception as e:
            print(f"❌ 查询数据库失败: {str(e)}")
            return []
        finally:
            if connection:
                connection.close()

    def extract_id_from_url(self, url):
        """
        从URL中解析最后等号后的ID

        Args:
            url (str): 输入的URL

        Returns:
            str: 解析出的ID，如果解析失败返回None
        """
        try:
            # 查找最后一个等号后的内容
            if '=' in url:
                id_value = url.split('=')[-1]
                # 移除可能的空格和其他字符
                id_value = re.sub(r'[^\d]', '', id_value)
                if id_value.isdigit():
                    return id_value
            return None
        except Exception as e:
            print(f"❌ 解析URL失败 {url}: {str(e)}")
            return None

    def check_gs_file(self, id_value):
        """
        调用API检查文件并获取data字符串

        Args:
            id_value (str): 要查询的ID

        Returns:
            str: 返回的data字符串，失败返回None
        """
        try:
            api_url = "https://ciac.zjw.sh.gov.cn/JGBXMJYPTInterWeb/api/zhcx/CheckHaveGsFile"
            payload = {"id": int(id_value)}

            print(f"🔍 正在查询ID: {id_value}")
            response = self.session.post(api_url, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0 and result.get('data'):
                    print(f"✅ 成功获取data字符串 (ID: {id_value})")
                    return result['data']
                else:
                    print(f"⚠️  API返回错误 (ID: {id_value}): {result.get('message', '未知错误')}")
                    return None
            else:
                print(f"❌ API请求失败 (ID: {id_value}): HTTP {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ 调用API失败 (ID: {id_value}): {str(e)}")
            return None

    def download_pdf(self, data_string, id_value, output_dir="downloads"):
        """
        下载PDF文件

        Args:
            data_string (str): API返回的data字符串
            id_value (str): 对应的ID
            output_dir (str): 输出目录

        Returns:
            bool: 下载是否成功
        """
        try:
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)

            data_string = quote(data_string, safe='')  # safe='' 表示不保留任何字符

            # 构建PDF查看URL
            pdf_url = f"https://ciac.zjw.sh.gov.cn/JGBFileViewInterWeb/#/pdfview?params={data_string}"

            print(f"📥 正在下载PDF (ID: {id_value})")

            # 直接请求PDF内容 - 可能需要调整这个URL
            # 注意：实际的PDF下载可能需要不同的URL端点
            #pdf_content_url = f"https://ciac.zjw.sh.gov.cn/JGBFileViewInterWeb/api/pdf/download?params={data_string}"
            pdf_content_url=f"https://ciac.zjw.sh.gov.cn/JGBFileViewInterWeb/file/pdf/download?params={data_string}"
            time.sleep(2)
            response = self.session.get(pdf_content_url, timeout=60)

            if response.status_code == 200:
                # 生成文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"pdf_{id_value}_{timestamp}.pdf"
                filepath = os.path.join(output_dir, filename)

                # 保存文件
                with open(filepath, 'wb') as f:
                    f.write(response.content)

                file_size = len(response.content)
                print(f"✅ PDF下载成功 (ID: {id_value}): {filepath} ({file_size} bytes)")
                return True
            else:
                print(f"❌ PDF下载失败 (ID: {id_value}): HTTP {response.status_code}")

                # 如果直接下载失败，保存data字符串供手动处理
                data_file = os.path.join(output_dir, f"data_{id_value}.txt")
                with open(data_file, 'w', encoding='utf-8') as f:
                    f.write(f"ID: {id_value}\n")
                    f.write(f"Data: {data_string}\n")
                    f.write(f"PDF URL: {pdf_url}\n")
                print(f"💾 已保存data字符串到: {data_file}")
                return False

        except Exception as e:
            print(f"❌ 下载PDF失败 (ID: {id_value}): {str(e)}")
            return False

    def process_all(self, output_dir="downloads"):
        """
        处理所有URL的完整流程

        Args:
            output_dir (str): 输出目录
        """
        print("🚀 开始处理...")

        # 1. 从数据库获取URL
        urls = self.get_urls_from_db()
        if not urls:
            print("❌ 没有获取到任何URL")
            return

        success_count = 0
        failed_count = 0

        # 2. 处理每个URL
        for i, url in enumerate(urls, 1):
            print(f"\n📍 处理进度: {i}/{len(urls)} - {url}")

            # 解析ID
            id_value = self.extract_id_from_url(url)
            if not id_value:
                print(f"⚠️  无法从URL解析ID: {url}")
                failed_count += 1
                continue

            # 调用API获取data
            data_string = self.check_gs_file(id_value)
            if not data_string:
                print(f"⚠️  无法获取data字符串 (ID: {id_value})")
                failed_count += 1
                continue

            # 下载PDF
            if self.download_pdf(data_string, id_value, output_dir):
                success_count += 1
            else:
                failed_count += 1

            # 添加延迟避免请求过频
            time.sleep(1)

        print(f"\n📊 处理完成:")
        print(f"   ✅ 成功: {success_count}")
        print(f"   ❌ 失败: {failed_count}")
        print(f"   📁 输出目录: {output_dir}")


def main():
    """主函数"""
    # 数据库配置 - 请根据实际情况修改
    db_config = {
        'username': 'zjw',
        'password': 'Ecloud2025',
        'host': '10.36.201.123',
        'port': '1521',
        'service_name': 'scgec'
    }

    # 创建下载器实例
    downloader = PDFDownloader(db_config)

    # 开始处理
    downloader.process_all()


if __name__ == "__main__":
    # 测试单个URL的示例
    def aa_single_url():
        """测试单个URL的处理"""
        db_config = {
             'username': 'zjw',
        'password': 'Ecloud2025',
        'host': '10.36.201.123',
        'port': '1521',
        'service_name': 'scgec'
        }

        downloader = PDFDownloader(db_config)

        # 测试URL
        test_url = "https://ciac.zjw.sh.gov.cn/JGBXMJYPTInterWeb/#/Hlwgg/GsfbInfo?zbgcid=80143"

        # 解析ID
        id_value = downloader.extract_id_from_url(test_url)
        print(f"解析的ID: {id_value}")

        if id_value:
            # 获取data字符串
            data_string = downloader.check_gs_file(id_value)
            if data_string:
                # 下载PDF
                downloader.download_pdf(data_string, id_value)


    # 取消注释下面的行来测试单个URL
    aa_single_url()

    # 运行完整流程
    #main()
