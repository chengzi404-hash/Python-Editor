# `modules/Uui/widgets/message_box.py`

源文件路径：`modules/Uui/widgets/message_box.py`

主题感知消息框（`showinfo/showwarning/showerror/askyesno`）的便捷封装。

## 内部基类

### `_UDialogBase(tk.Toplevel)`
基础居中对话框：自动 `transient(parent)` / `grab_set()` / 居中几何。

## 公开函数

- `showinfo(title, message, parent=None) -> None`
- `showwarning(title, message, parent=None) -> None`
- `showerror(title, message, parent=None) -> None`
- `askyesno(title, message, parent=None) -> bool`
- `askokcancel(title, message, parent=None) -> bool`
- `askretrycancel(title, message, parent=None) -> bool`

所有函数都返回 `None` 或 `bool`；阻塞父窗口（`grab_set`），关闭后释放。

## `__all__`

```python
['showinfo', 'showwarning', 'showerror',
 'askyesno', 'askokcancel', 'askretrycancel']
```

（具体导出见源码顶部。）