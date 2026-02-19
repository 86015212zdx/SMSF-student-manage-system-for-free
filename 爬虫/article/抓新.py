import os

import requests
import re
from one import one_main
from ai加工 import demo_usage_ai
from db_importer import demo_usage
import time

headers = {}
response = requests.get('', headers=headers)
# print(response.text)
pp = r"<a href=\"\/essays\/(.*?)\">"

aa = re.findall(pp, response.text)


def cleanup_txt_files():
    """删除多余的.txt文件，保留all_res.txt和data.txt"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    exclude_files = {'all_res.txt', 'data.txt'}  # 要保留的文件

    # 获取所有.txt文件
    txt_files = [f for f in os.listdir(current_dir) if f.endswith('.txt')]

    # 找出需要删除的文件
    files_to_delete = [f for f in txt_files if f not in exclude_files]

    if files_to_delete:
        print(f"🗑️ 准备删除 {len(files_to_delete)} 个多余文件:")
        for file in files_to_delete:
            file_path = os.path.join(current_dir, file)
            try:
                os.remove(file_path)
                print(f"   ✅ 已删除: {file}")
            except Exception as e:
                print(f"   ❌ 删除失败 {file}: {str(e)}")
        print("清理完成！")
    else:
        print("✅ 没有需要删除的多余文件")


for i in aa:
    print(i)
with open("data.txt", "a", encoding="utf-8") as f:
    for i in aa:
        f.write(i + "\n")
print("写入完成,正在比对已有数据")

with open("all_res.txt", "r", encoding="utf-8") as f:
    now_had = [line.strip() for line in f.readlines()]
    print(f"已获取{len(now_had)}条数据")

diff = list(set(aa) - set(now_had))

print(f"共有{len(diff)}条数据未获取")
for i in diff:
    print(i)

print("开始更新")
for i in diff:
    one_main(r""+i)
    demo_usage()
    demo_usage_ai()
    print(f"更新完成{i},等待中。。。")
    cleanup_txt_files()
    with open("all_res.txt", "a", encoding="utf-8") as f:
        f.write(i + "\n")
    time.sleep(10)

os.remove("data.txt")
