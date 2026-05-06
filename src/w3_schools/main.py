import httpx
import subprocess
import sys
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Tree, ContentSwitcher, LoadingIndicator, Markdown, Button
from textual.containers import Horizontal, VerticalScroll, Container, Vertical
from textual.reactive import reactive
from textual.binding import Binding
from textual.screen import Screen

BASE_URL = "https://www.w3schools.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

CATEGORIES = {
    "HTML": "html",
    "CSS": "css",
    "JavaScript": "js",
    "Python": "python",
    "SQL": "sql",
    "Java": "java",
    "PHP": "php",
    "C++": "cpp",
    "C#": "cs",
    "React": "react",
    "Bootstrap": "bootstrap",
}

class CategorySelect(Screen):
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Select a Tutorial to Begin:", id="title")
        with VerticalScroll(id="cat-list"):
            for name, path in CATEGORIES.items():
                yield Button(name, id=path, variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.app.current_category = event.button.id
        self.app.push_screen(LessonScreen())

class LessonScreen(Screen):
    show_sidebar = reactive(True)
    BINDINGS = [
        Binding("b", "toggle_sidebar", "Toggle Sidebar"),
        Binding("escape", "back_to_menu", "Back to Menu"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Button("☰ Menu", id="toggle-sidebar-btn", variant="default")
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Button("⬅ Exit Tutorial", id="back-btn", variant="error")
                yield Tree("Lessons", id="lesson-tree")
            with ContentSwitcher(initial="loading", id="content-area"):
                yield LoadingIndicator(id="loading")
                with VerticalScroll(id="viewer-container"):
                    yield Markdown("", id="markdown-viewer")
        yield Footer()

    def on_markdown_link_clicked(self, event: Markdown.LinkClicked) -> None:
        url = event.href
        if url.startswith('/'): url = BASE_URL + url
        try:
            subprocess.run(["termux-open", url], check=True)
            self.notify(f"Opening browser: {url[:30]}...")
        except Exception as e:
            self.notify(f"Could not open browser: {e}", severity="error")

    def watch_show_sidebar(self, show_sidebar: bool) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.display = "block" if show_sidebar else "none"

    def action_toggle_sidebar(self) -> None:
        self.show_sidebar = not self.show_sidebar

    def action_back_to_menu(self) -> None:
        self.app.pop_screen()

    async def on_mount(self) -> None:
        self.show_sidebar = True
        await self.load_lessons(self.app.current_category)

    async def load_lessons(self, category: str):
        tree = self.query_one("#lesson-tree", Tree)
        tree.root.label = f"{category.upper()} Tutorial"
        try:
            url = f"{BASE_URL}/{category}/default.asp"
            async with httpx.AsyncClient(headers=HEADERS) as client:
                response = await client.get(url, follow_redirects=True)
                soup = BeautifulSoup(response.text, 'html.parser')
                left_menu = soup.find('div', id="leftmenuinnerinner")
                if left_menu:
                    lessons = left_menu.find_all('a', target="_top")
                    seen = set()
                    for lesson in lessons:
                        text = lesson.text.strip()
                        href = lesson['href']
                        if text and text not in seen:
                            tree.root.add_leaf(text, data=f"{category}/{href}")
                            seen.add(text)
                tree.root.expand()
                await self.load_lesson_content(f"{category}/default.asp")
        except Exception as e:
            self.notify(f"Error loading lessons: {e}", severity="error")

    async def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data:
            self.query_one("#content-area").current = "loading"
            await self.load_lesson_content(event.node.data)

    async def load_lesson_content(self, rel_url: str):
        try:
            url = f"{BASE_URL}/{rel_url}"
            async with httpx.AsyncClient(headers=HEADERS) as client:
                response = await client.get(url, follow_redirects=True)
                soup = BeautifulSoup(response.text, 'html.parser')
                main_content = soup.find('div', id="main")
                if main_content:
                    md_lines = []
                    for elem in main_content.find_all(['h1', 'h2', 'h3', 'p', 'pre', 'div', 'ul', 'ol', 'table']):
                        if elem.name.startswith('h'):
                            level = "#" * int(elem.name[1])
                            md_lines.append(f"{level} {elem.get_text(strip=True)}")
                        elif elem.name == 'p':
                            p_html = str(elem)
                            p_soup = BeautifulSoup(p_html, 'html.parser')
                            for a in p_soup.find_all('a', href=True):
                                a.replace_with(f"[{a.text.strip()}]({a['href']})")
                            md_lines.append(p_soup.get_text(strip=True))
                        elif elem.name in ['ul', 'ol']:
                            for li in elem.find_all('li'):
                                for a in li.find_all('a', href=True):
                                    a.replace_with(f"[{a.text.strip()}]({a['href']})")
                                md_lines.append(f"* {li.get_text(strip=True)}")
                        elif elem.name == 'pre' or (elem.name == 'div' and ('w3-code' in elem.get('class', []) or 'w3-example' in elem.get('class', []))):
                            code = elem.get_text().strip()
                            if "Try it Yourself" in code:
                                code = code.split("Try it Yourself")[0].strip()
                            md_lines.append(f"```html\n{code}\n```")
                        elif elem.name == 'table':
                            md_lines.append("\n[Table detected - see original for layout]\n")
                        md_lines.append("")
                    self.query_one("#markdown-viewer", Markdown).update("\n".join(md_lines))
                self.query_one("#content-area").current = "viewer-container"
        except Exception as e:
            self.notify(f"Error loading content: {e}", severity="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "toggle-sidebar-btn":
            self.action_toggle_sidebar()

class W3SchoolsApp(App):
    TITLE = "W3Schools Termux"
    CSS = """
    #title { text-align: center; width: 100%; padding: 1; background: $accent; color: white; text-style: bold; }
    #cat-list { align: center middle; padding: 2; }
    #cat-list Button { width: 40; margin: 1; }
    #toggle-sidebar-btn { width: 15; height: 3; margin: 0; border: none; background: $primary; color: white; }
    #sidebar { width: 35; height: 100%; background: #252526; border-right: tall $primary; }
    #back-btn { width: 100%; margin-bottom: 1; }
    #content-area { height: 100%; padding: 1; }
    Markdown { background: transparent; }
    """
    current_category = reactive("html")
    def on_mount(self) -> None:
        self.push_screen(CategorySelect())

def run():
    if "--info" in sys.argv:
        console = Console()
        info_text = Text.assemble(
            ("\n📦 Package Overview\n", "bold cyan"),
            ("Name: ", "bold"), "w3-schools\n",
            ("Version: ", "bold"), "0.1.5\n",
            ("Summary: ", "bold"), "Terminal UI for learning from W3Schools\n",
            ("License: ", "bold"), "MIT\n",
            ("\n👤 Author\n", "bold green"),
            ("Name: ", "bold"), "kyle Votes\n",
            ("Email: ", "bold"), "kylevotes@gmail.com\n",
            ("\n📂 Installation\n", "bold yellow"),
            ("Location: ", "bold"), f"{sys.prefix}/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages\n",
            ("\n🔗 Dependencies\n", "bold magenta"),
            ("- beautifulsoup4\n", ""),
            ("- httpx\n", ""),
            ("- textual\n", ""),
            ("\n📌 Notes\n", "bold blue"),
            ("- Installed in global environment (not isolated)\n", ""),
            ("- Designed for Termux CLI usage\n", "")
        )
        console.print(Panel(info_text, title="[bold white]w3-schools INFO[/]", border_style="cyan", expand=False))
        sys.exit(0)

    app = W3SchoolsApp()
    app.run()

if __name__ == "__main__":
    run()
