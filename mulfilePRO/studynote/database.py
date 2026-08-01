# -*- coding: utf-8 -*-

import sqlite3

class NoteDatabase:
    def __init__(self, db_name="notes_app.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        with self.conn:
            # 笔记本表
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS notebooks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
            """)
            # 笔记表（含 is_deleted 软删除字段与 is_md 模式标记）
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    notebook_id INTEGER,
                    title TEXT NOT NULL,
                    content TEXT,
                    tags TEXT,
                    is_markdown INTEGER DEFAULT 0,
                    is_deleted INTEGER DEFAULT 0,
                    FOREIGN KEY(notebook_id) REFERENCES notebooks(id)
                )
            """)
        
        # 默认初始化一个笔记本和笔记（如果为空）
        if len(self.get_all_notebooks()) == 0:
            self.add_notebook("默认笔记本")
            self.add_note(1, "欢迎使用", "# 欢迎使用现代化笔记软件\n- 支持 Markdown 与富文本切换\n- 支持回收站与视觉反馈", "指南", 0)

    def get_all_notebooks(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM notebooks")
        return cursor.fetchall()

    def add_notebook(self, name):
        with self.conn:
            self.conn.execute("INSERT INTO notebooks (name) VALUES (?)", (name,))

    def update_notebook_name(self, notebook_id, new_name):
        """更新笔记本名称"""
        with self.conn:
            self.conn.execute("UPDATE notebooks SET name = ? WHERE id = ?", (new_name, notebook_id))

    def delete_notebook(self, notebook_id):
        with self.conn:
            self.conn.execute("DELETE FROM notes WHERE notebook_id = ?", (notebook_id,))
            self.conn.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))

    def get_notes_by_notebook(self, notebook_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title FROM notes WHERE notebook_id = ? AND is_deleted = 0", (notebook_id,))
        return cursor.fetchall()

    def get_deleted_notes(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title FROM notes WHERE is_deleted = 1")
        return cursor.fetchall()

    def get_note_by_id(self, note_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT title, content, tags, notebook_id, is_markdown, is_deleted FROM notes WHERE id = ?", (note_id,))
        return cursor.fetchone()

    def add_note(self, notebook_id, title, content, tags, is_markdown):
        with self.conn:
            self.conn.execute(
                "INSERT INTO notes (notebook_id, title, content, tags, is_markdown, is_deleted) VALUES (?, ?, ?, ?, ?, 0)",
                (notebook_id, title, content, tags, is_markdown)
            )

    def update_note(self, note_id, title, content, tags, is_markdown):
        with self.conn:
            self.conn.execute(
                "UPDATE notes SET title = ?, content = ?, tags = ?, is_markdown = ? WHERE id = ?",
                (title, content, tags, is_markdown, note_id)
            )

    def soft_delete_note(self, note_id):
        with self.conn:
            self.conn.execute("UPDATE notes SET is_deleted = 1 WHERE id = ?", (note_id,))

    def restore_note(self, note_id):
        with self.conn:
            self.conn.execute("UPDATE notes SET is_deleted = 0 WHERE id = ?", (note_id,))

    def permanent_delete_note(self, note_id):
        with self.conn:
            self.conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))

    def count_active_notes(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notes WHERE is_deleted = 0")
        return cursor.fetchone()[0]

    def get_all_tags(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT DISTINCT tags FROM notes WHERE tags IS NOT NULL AND tags != '' AND is_deleted = 0")
        rows = cursor.fetchall()
        tags_set = set()
        for row in rows:
            for t in row[0].split(','):
                if t.strip():
                    tags_set.add(t.strip())
        return list(tags_set)

    def get_notes_by_tag(self, tag):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title FROM notes WHERE tags LIKE ? AND is_deleted = 0", (f"%{tag}%",))
        return cursor.fetchall()

    def search_notes(self, keyword):
        cursor = self.conn.cursor()
        keyword_param = f"%{keyword}%"
        cursor.execute("SELECT id, title FROM notes WHERE (title LIKE ? OR content LIKE ?) AND is_deleted = 0", (keyword_param, keyword_param))
        return cursor.fetchall()