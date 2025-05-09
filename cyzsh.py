import random
import time
import asyncio
import aiohttp
import re
import os
import json
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional, Tuple, Union
import requests

class LocalDBManager:
    def __init__(self):
        self.db_file = "resources.json"
        # Create the file if it doesn't exist
        if not os.path.exists(self.db_file):
            with open(self.db_file, 'w') as f:
                json.dump([], f)
    
    def _save_resources(self, resources: List) -> None:
        with open(self.db_file, 'w') as f:
            json.dump(resources, f)
    
    def get_resources(self) -> List:
        with open(self.db_file, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    
    def add_resource(self, resource: Dict) -> None:
        resources = self.get_resources()
        resources.append(resource)
        self._save_resources(resources)
    
    def remove_resource(self, index: int) -> bool:
        resources = self.get_resources()
        if 0 <= index < len(resources):
            del resources[index]
            self._save_resources(resources)
            return True
        return False

class FacebookAutoShare:
    def __init__(self):
        with open("config.json") as f:
            config = json.load(f)
            self.version = config["VERSION"]
            self.dev = config["DEV"]
        self.console = Console()
        self.api_version = 'v22.0'
        self.user_agents = self._generate_user_agents()
        self.user_agent = random.choice(self.user_agents)
        self.session = None
        self.executor = ThreadPoolExecutor(max_workers=100)
        self.connector = aiohttp.TCPConnector(limit=0, force_close=True)
        self.concurrent = 17
        self.start_time = None
        self.error_log = []
        self.db = LocalDBManager()
        self.interval = 0
        self.REQUEST_TIMEOUT = 30
        self.current_menu = "main"

    def _generate_user_agents(self):
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
        ]

    @staticmethod
    def get_headers(cookie: str = None) -> Dict:
        headers = {
            "User-Agent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
            ]),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }
        if cookie:
            headers["Cookie"] = cookie
        return headers

    def loading(self, duration: float = 2, message: str = "Processing") -> None:
        symbols = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']
        end_time = time.time() + duration
        while time.time() < end_time:
            for symbol in symbols:
                print(f"\033[94m  {symbol} {message}...\033[0m", end='\r')
                time.sleep(0.1)
        print(" " * (len(message) + 10), end='\r')

    def print_panel(self, title, content, color):
        self.console.print(Panel(content, title=title, width=None, padding=(0, 3), style=color))

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def show_banner(self):
        banner = r"""
███████╗███████╗██╗  ██╗ █████╗ ██████╗ ███████╗
██╔════╝██╔════╝██║  ██║██╔══██╗██╔══██╗██╔════╝
█████╗  ███████╗███████║███████║██████╔╝█████╗  
██╔══╝  ╚════██║██╔══██║██╔══██║██╔══██╗██╔══╝  
██║     ███████║██║  ██║██║  ██║██║  ██║███████╗
╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
        """
        menu_modes = {
            'main': 'Main Menu',
            'share': 'Spam Share',
            'resources': 'Resource Management'
        }
        current_mode = menu_modes.get(self.current_menu, 'Main Menu')
        
        info = f"""
[›] Tool: FB Spam Share
[›] Version: {self.version}
[›] Dev: {self.dev}
[›] Panel: {current_mode}
        """
        self.print_panel('CYZSH', banner, "violet")
        self.print_panel('Info', info, "violet")

    def show_main_menu(self):
        self.current_menu = "main"
        self.clear_screen()
        self.show_banner()
        self.print_panel(
            "Main Menu",
            "[1] Initialize Spamshare\n"
            "[2] Manage Resources\n"
            "[3] Exit",
            "blue"
        )

    def show_share_menu(self):
        self.current_menu = "share"
        self.clear_screen()
        self.show_banner()
        self.print_panel(
            "Spam Share",
            "[1] Share as User\n"
            "[2] Share as Page\n"
            "[3] Combined Sharing\n"
            "[0] Back to Main",
            "blue"
        )

    async def show_resource_management(self):
        self.current_menu = "resources"
        self.clear_screen()
        self.show_banner()
        
        resources = self.db.get_resources()
        
        # Create table
        table = Table(
            title=f"[bold magenta]Resources[/] (Testing {len(resources)} entries...)",
            show_header=True,
            header_style="bold cyan",
            width=59
        )
        
        table.add_column("#", style="dim", width=4)
        table.add_column("Type", width=8)
        table.add_column("Content", width=12)
        table.add_column("Status", width=12)
        table.add_column("Details", width=16)
    
        # Test each resource
        tested_resources = []
        with Progress(transient=True) as progress:
            task = progress.add_task("Validating...", total=len(resources))
            
            for idx, resource in enumerate(resources):
                status = ""
                details = ""
                
                if isinstance(resource, dict):
                    if 'cookie' in resource:
                        # Test cookie
                        token = self.get_token_from_cookie(resource['cookie'])
                        if token:
                            test_result = await self.verify_token(token)
                            status = "[green]✓ LIVE[/]" if test_result['valid'] else "[red]DEAD[/]"
                            details = f"{len(test_result.get('pages', []))} pages" if test_result['valid'] else "Invalid"
                        else:
                            status = "[red]INVALID[/]"
                            details = "Bad cookie"
                        
                        tested_resources.append({
                            'type': "Cookie",
                            'content': resource['cookie'],
                            'status': status,
                            'details': details
                        })
                        
                    elif 'token' in resource:
                        # Test token directly
                        test_result = await self.verify_token(resource['token'])
                        if test_result['valid']:
                            status = "[green]✓ LIVE[/]"
                            details = f"{len(test_result.get('pages', []))} pages"
                        else:
                            status = "[red]DEAD[/]"
                            details = test_result.get('error', 'Invalid')[:12]
                        
                        tested_resources.append({
                            'type': "Token",
                            'content': resource['token'],
                            'status': status,
                            'details': details
                        })
                
                progress.update(task, advance=1)
                await asyncio.sleep(0.1)  # Prevent rate limiting
    
        # Build table with verified results
        for idx, res in enumerate(tested_resources):
            content_preview = (res['content'][:7] + '...') if len(res['content']) > 19 else res['content']
            table.add_row(
                str(idx),
                res['type'],
                content_preview,
                res['status'],
                res['details']
            )
    
        self.console.print(table)
        self.print_panel(
            "Controls",
            "[1] Add  [2] Remove  [3] Test All  [0] Back",
            "blue"
        )

    async def create_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                headers={'User-Agent': self.user_agent},
                timeout=aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
            )

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()
        self.executor.shutdown(wait=True)

    def get_token_from_cookie(self, cookie: str) -> Optional[str]:
        try:
            response = requests.get(
                "https://business.facebook.com/content_management",
                headers=self.get_headers(cookie),
                timeout=self.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            token = response.text.split("EAAG")[1].split('","')[0]
            return f"EAAG{token}"
        except Exception as e:
            self.error_log.append(f"Cookie Error: {str(e)}")
            return None

    def load_tokens(self) -> List[Dict]:
        resources = self.db.get_resources()
        valid_tokens = []
        
        for item in resources:
            if isinstance(item, dict):
                if item.get('token'):
                    valid_tokens.append({'token': item['token'], 'type': 'token'})
                elif item.get('cookie'):
                    token = self.get_token_from_cookie(item['cookie'])
                    if token:
                        valid_tokens.append({'token': token, 'type': 'cookie'})
        return valid_tokens

    async def verify_token(self, token: str) -> Dict:
        try:
            await self.create_session()
            async with self.session.get(
                f"https://graph.facebook.com/{self.api_version}/me/accounts",
                params={'access_token': token},
                timeout=10
            ) as resp:
                data = await resp.json()
                if resp.status == 200:
                    pages = [{
                        'name': page['name'],
                        'access_token': page['access_token'],
                        'id': page['id']
                    } for page in data.get('data', [])]
                    return {'valid': True, 'pages': pages}
                return {'valid': False, 'error': data.get('error', {}).get('message', 'Unknown error')}
        except Exception as e:
            return {'valid': False, 'error': str(e)}

    async def get_post_id(self, post_link: str) -> Optional[str]:
        """Extract post ID from URL"""
        self.loading(2, "Finding post ID")
        try:
            await self.create_session()
            async with self.session.post(
                "https://id.traodoisub.com/api.php",
                data={"link": post_link},
                timeout=10
            ) as resp:
                if (await resp.json()).get('id'):
                    return (await resp.json())['id']

            patterns = [
                r'facebook\.com\/.+\/(?:posts|photos|activity)\/(\d+)',
                r'story_fbid=(\d+)&id=(\d+)',
                r'facebook\.com\/(\d+_\d+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, post_link)
                if match:
                    return f"{match.group(1)}_{match.group(2)}" if len(match.groups()) > 1 else match.group(1)
            return None
        except Exception as e:
            self.print_panel("", f"Failed to get post ID: {str(e)}", "red")
            self.error_log.append(f"Post ID Error: {str(e)}")
            return None

    async def perform_share(self, token: str, target_id: str, is_page: bool = False) -> bool:
        try:
            params = {
                "link": f"https://m.facebook.com/{target_id}",
                "published": "0",
                "access_token": token
            }
            endpoint = f"{target_id}/feed" if is_page else "me/feed"
            
            async with self.session.post(
                f"https://graph.facebook.com/{self.api_version}/{endpoint}",
                params=params,
                timeout=5
            ) as resp:
                data = await resp.json()
                if resp.status != 200:
                    self.error_log.append(f"Share Error: {data.get('error', {}).get('message', 'Unknown error')}")
                    return False
                return data.get('id') is not None
        except Exception as e:
            self.error_log.append(f"Share Exception: {str(e)}")
            return False

    async def burst_share(self, share_type: int, post_id: str, total_shares: int) -> Tuple[int, int]:
        tokens = self.load_tokens()
        pages = []
        
        if share_type in [2, 3]:
            for token_data in tokens.copy():
                result = await self.verify_token(token_data['token'])
                if result['valid'] and result.get('pages'):
                    pages.extend(result['pages'])
                    if share_type == 2:  # Pages only mode
                        tokens.remove(token_data)

        success = failed = 0
        self.start_time = time.time()
        
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            transient=True
        ) as progress:
            task = progress.add_task("Sharing...", total=total_shares)
            
            while success + failed < total_shares:
                try:
                    if share_type == 1 and tokens:  # User only
                        token = random.choice(tokens)['token']
                        result = await self.perform_share(token, post_id)
                    elif share_type == 2 and pages:  # Page only
                        page = random.choice(pages)
                        result = await self.perform_share(page['access_token'], page['id'], True)
                    elif share_type == 3:  # Combined
                        if tokens and (not pages or random.choice([True, False])):
                            token = random.choice(tokens)['token']
                            result = await self.perform_share(token, post_id)
                        elif pages:
                            page = random.choice(pages)
                            result = await self.perform_share(page['access_token'], page['id'], True)
                        else:
                            break
                    else:
                        break
                    
                    if result:
                        success += 1
                    else:
                        failed += 1
                    
                    progress.update(task, advance=1)
                    
                    if self.interval > 0:
                        await asyncio.sleep(self.interval)
                except Exception as e:
                    failed += 1
                    self.error_log.append(f"Task Error: {str(e)}")
        
        return success, failed

    async def run_share_process(self, share_type: int, post_link: str, total_shares: int):
        self.clear_screen()
        self.show_banner()
        
        post_id = await self.get_post_id(post_link)
        if not post_id:
            self.print_panel("Error", "Failed to get post ID", "red")
            return
        
        self.print_panel("Info", f"Post ID: {post_id}", "green")
        
        tokens = self.load_tokens()
        if not tokens:
            self.print_panel("Error", "No valid tokens/cookies found", "red")
            return
        
        self.print_panel("Status", f"Starting {total_shares} shares...", "blue")
        success, failed = await self.burst_share(share_type, post_id, total_shares)
        elapsed = time.time() - self.start_time
        
        self.print_panel("Results",
            f"Success: {success}\n"
            f"Failed: {failed}\n"
            f"Time: {elapsed:.2f}s\n"
            f"Speed: {success/max(1, elapsed):.1f}/s",
            "green" if success >= total_shares * 0.7 else "yellow"
        )

    async def run(self):
        while True:
            if self.current_menu == "main":
                self.show_main_menu()
                choice = input("\n[›] Select: ")
                
                if choice == "1":
                    self.show_share_menu()
                elif choice == "2":
                    await self.manage_resources()
                elif choice == "3":
                    break
                
            elif self.current_menu == "share":
                self.show_share_menu()
                choice = input("\n[›] Select: ")
                
                if choice == "0":
                    self.current_menu = "main"
                elif choice in ["1", "2", "3"]:
                    post_link = input("[›] Post URL: ")
                    amount = int(input("[›] Share count: ") or 5)
                    self.interval = float(input("[›] Delay (seconds): ") or 3)
                    
                    await self.run_share_process(int(choice), post_link, amount)
                    input("\n[Press Enter to continue]")
                else:
                    self.print_panel("Error", "Invalid choice", "red")
                    time.sleep(1)

    async def manage_resources(self):
        while True:
            await self.show_resource_management()
            choice = input("\n[›] Select: ")
            
            if choice == "0":
                self.current_menu = "main"
                break
            elif choice == "1":
                resource = input("[›] Enter cookie/token: ").strip()
                if not resource:
                    self.print_panel("Error", "Cannot be empty", "red")
                else:
                    resource_type = 'cookie' if ('c_user=' in resource or 'xs=' in resource) else 'token'
                    self.db.add_resource({resource_type: resource})
                    self.print_panel("Success", "Resource added!", "green")
                time.sleep(1)
            elif choice == "2":
                try:
                    index = int(input("[›] Index to remove: "))
                    if self.db.remove_resource(index):
                        self.print_panel("Success", "Resource removed!", "green")
                    else:
                        self.print_panel("Error", "Invalid index", "red")
                    time.sleep(1)
                except ValueError:
                    self.print_panel("Error", "Enter a number", "red")
                    time.sleep(1)
            elif choice == "3":
                await self.show_resource_management()
                time.sleep(1)
            else:
                self.print_panel("Error", "Invalid choice", "red")
                time.sleep(1)

async def main():
    tool = FacebookAutoShare()
    try:
        await tool.run()
    finally:
        await tool.close_session()

if __name__ == "__main__":
    asyncio.run(main())
