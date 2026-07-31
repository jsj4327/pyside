# -*- coding:utf-8 -*-

"""
BugNote v2

models.py

负责:
    - Issue数据模型
    - 本地存储
    - Markdown导出

不负责:
    - UI
    - PySide2
"""


import os
import json
import datetime





DATA_DIR = "bugnote_data"


ISSUE_DIR = os.path.join(
    DATA_DIR,
    "issues"
)


EXPORT_DIR = os.path.join(
    DATA_DIR,
    "exports"
)






class IssueModel:
    """
    一个Bug记录对象
    """



    def __init__(self):


        # 标题

        self.title = ""



        # 问题描述

        self.description = ""



        # 类型

        self.issue_type = "Bug"



        # 严重等级

        self.level = "Medium"



        # 当前状态

        self.status = "待分析"



        # AI任务类型

        self.task_type = "Bug分析"



        # 所属模块

        self.modules = []



        # 项目信息

        self.project = {

            "name": "",
            "branch": "",
            "commit": ""

        }



        # 当前代码上下文

        self.context = {

            "file": "",
            "line": ""

        }



        # 异常信息

        self.traceback = ""



        # 日志

        self.log = ""



        # 标签

        self.tags = ""



        # 环境

        self.environment = {}



        # 创建时间

        self.created = ""





    def to_dict(self):
        """
        转换为JSON数据
        """


        return {


            "title":
                self.title,


            "description":
                self.description,


            "type":
                self.issue_type,


            "level":
                self.level,


            "status":
                self.status,


            "task_type":
                self.task_type,


            "modules":
                self.modules,


            "project":
                self.project,


            "context":
                self.context,


            "traceback":
                self.traceback,


            "log":
                self.log,


            "tags":
                self.tags,


            "environment":
                self.environment,


            "created":
                self.created

        }






    @staticmethod
    def from_dict(data):
        """
        JSON恢复对象
        """


        obj = IssueModel()



        obj.title = data.get(
            "title",
            ""
        )



        obj.description = data.get(
            "description",
            ""
        )



        obj.issue_type = data.get(
            "type",
            "Bug"
        )



        obj.level = data.get(
            "level",
            "Medium"
        )



        obj.status = data.get(
            "status",
            "待分析"
        )



        obj.task_type = data.get(
            "task_type",
            "Bug分析"
        )



        obj.modules = data.get(
            "modules",
            []
        )



        obj.project = data.get(
            "project",
            {}
        )



        obj.context = data.get(
            "context",
            {}
        )



        obj.traceback = data.get(
            "traceback",
            ""
        )



        obj.log = data.get(
            "log",
            ""
        )



        obj.tags = data.get(
            "tags",
            ""
        )



        obj.environment = data.get(
            "environment",
            {}
        )



        obj.created = data.get(
            "created",
            ""
        )


        return obj











class IssueStorage:
    """
    Issue文件管理
    """



    def __init__(self):


        os.makedirs(
            ISSUE_DIR,
            exist_ok=True
        )


        os.makedirs(
            EXPORT_DIR,
            exist_ok=True
        )







    def save(self, issue):
        """
        保存JSON
        """


        filename = datetime.datetime.now().strftime(
            "issue_%Y%m%d_%H%M%S.json"
        )


        path = os.path.join(
            ISSUE_DIR,
            filename
        )



        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(
                issue.to_dict(),
                f,
                ensure_ascii=False,
                indent=4
            )



        return path








    def load_all(self):
        """
        加载所有Issue

        返回:
        [
            (文件路径, Issue对象)
        ]
        """



        result = []



        if not os.path.exists(
            ISSUE_DIR
        ):

            return result




        for filename in os.listdir(
            ISSUE_DIR
        ):



            if not filename.endswith(
                ".json"
            ):

                continue




            path = os.path.join(
                ISSUE_DIR,
                filename
            )



            try:


                with open(
                    path,
                    "r",
                    encoding="utf-8"
                ) as f:


                    data = json.load(f)



                issue = IssueModel.from_dict(
                    data
                )


                result.append(
                    (
                        path,
                        issue
                    )
                )


            except Exception:


                pass






        return sorted(

            result,

            key=lambda x:
                x[1].created,

            reverse=True

        )










    def export_markdown(self, issue):
        """
        导出Markdown，
        方便提交给AI
        """



        filename = datetime.datetime.now().strftime(
            "issue_%Y%m%d_%H%M%S.md"
        )



        path = os.path.join(
            EXPORT_DIR,
            filename
        )



        text = f"""
# {issue.title}


## 基本信息

类型:
{issue.issue_type}


等级:
{issue.level}


状态:
{issue.status}


AI任务:
{issue.task_type}



## 描述

{issue.description}



## 模块

{", ".join(issue.modules)}



## 项目

```json
{json.dumps(
    issue.project,
    ensure_ascii=False,
    indent=4
)}