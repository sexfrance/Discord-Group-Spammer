import random
import time
import toml
import ctypes
import threading
import tls_client
import base64
import json
import uuid

from concurrent.futures import ThreadPoolExecutor, as_completed
from logmagix import Logger, Home
from functools import wraps

with open('input/config.toml') as f:
    config = toml.load(f)

DEBUG = config['dev'].get('Debug', False)

log = Logger()

def debug(func_or_message, *args, **kwargs) -> callable:
    if callable(func_or_message):
        @wraps(func_or_message)
        def wrapper(*args, **kwargs):
            result = func_or_message(*args, **kwargs)
            if DEBUG:
                log.debug(f"{func_or_message.__name__} returned: {result}")
            return result
        return wrapper
    else:
        if DEBUG:
            log.debug(f"Debug: {func_or_message}")

def debug_response(response) -> None:
    debug(response.headers)
    try:
        debug(response.text)
    except:
        debug(response.content)
    debug(response.status_code)

class Miscellaneous:
    @debug
    def get_proxies(self) -> dict:
        try:
            if config['dev'].get('Proxyless', False):
                return None
            with open('input/proxies.txt') as f:
                proxies = [line.strip() for line in f if line.strip()]
                if not proxies:
                    log.warning("No proxies available. Running in proxyless mode.")
                    return None
                proxy_choice = random.choice(proxies)
                proxy_dict = {
                    "http": f"http://{proxy_choice}",
                    "https": f"http://{proxy_choice}"
                }
                debug(f"Using proxy: {proxy_choice}")
                return proxy_dict
        except FileNotFoundError:
            log.failure("Proxy file not found. Running in proxyless mode.")
            return None

    @debug
    def randomize_user_agent(self) -> tuple[str, str, str, str, str, str]:
        platforms = {
            "Windows NT 10.0; Win64; x64": "Windows",
            "Windows NT 10.0; WOW64": "Windows",
            "Macintosh; Intel Mac OS X 10_15_7": "Mac OS X",
            "Macintosh; Intel Mac OS X 11_2_3": "Mac OS X",
            "X11; Linux x86_64": "Linux",
            "X11; Ubuntu; Linux x86_64": "Linux",
        }
        discord_version = f"1.0.{random.randint(1000, 1200)}"
        chrome_version_major = random.randint(120, 135)
        chrome_version = f"{chrome_version_major}.0.{random.randint(6000, 7000)}.{random.randint(100, 200)}"
        electron_version = f"{random.randint(25, 35)}.{random.randint(0, 5)}.{random.randint(0, 10)}"
        webkit_version = f"{random.randint(500, 600)}.{random.randint(0, 99)}"
        platform_string = random.choice(list(platforms.keys()))
        platform_os = platforms[platform_string]
        user_agent = (
            f"Mozilla/5.0 ({platform_string}) AppleWebKit/{webkit_version} (KHTML, like Gecko) "
            f"discord/{discord_version} Chrome/{chrome_version} Electron/{electron_version} Safari/{webkit_version}"
        )
        return user_agent, platform_os, discord_version, chrome_version, electron_version, chrome_version_major

    class Title:
        def __init__(self) -> None:
            self.running = False
            self.total = 0

        def start_title_updates(self, start_time) -> None:
            self.running = True
            def updater():
                while self.running:
                    self.update_title(start_time)
                    time.sleep(0.5)
            threading.Thread(target=updater, daemon=True).start()

        def stop_title_updates(self) -> None:
            self.running = False

        def update_title(self, start_time) -> None: 
            try:
                elapsed_time = round(time.time() - start_time, 2)
                title = f'discord.cyberious.xyz | Total: {self.total} | Time Elapsed: {elapsed_time}s'
                sanitized_title = ''.join(c if c.isprintable() else '?' for c in title)
                ctypes.windll.kernel32.SetConsoleTitleW(sanitized_title)
            except Exception as e:
                log.failure(f"Failed to update console title: {e}")

        def increment_total(self):
            self.total += 1

class GroupCreator:
    def __init__(self, misc: Miscellaneous, token: str, proxy_dict: dict = None) -> None:
        self.misc = misc
        user_agent, os_name, discord_version, chrome_version, electron_version, chrome_version_major = self.misc.randomize_user_agent()
        self.session = tls_client.Session(client_identifier="chrome_133", random_tls_extension_order=True)
        self.session.headers = {
            'accept': '*/*',
            'accept-language': 'fr,fr-FR;q=0.9', 
            'authorization': token,
            'origin': 'https://ptb.discord.com',
            'priority': 'u=1, i',
            'sec-ch-ua': f'"Not:A-Brand";v="24", "Chromium";v="{chrome_version_major}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': f'"{os_name}"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': user_agent, 
            'x-context-properties': 'eyJsb2NhdGlvbiI6IkFkZCBGcmllbmRzIHRvIERNIn0=',
            'x-debug-options': 'bugReporterEnabled',
            'x-discord-locale': 'en-US', 
            'x-discord-timezone': 'Europe/Paris',
            'x-super-properties': self.generate_super_properties(os_name, discord_version, user_agent, electron_version),
        }
        self.session.proxies = proxy_dict

    @debug
    def generate_super_properties(self, os_name: str, discord_version: str, user_agent: str, electron_version: str) -> str:
        client_build_number = random.randint(300000, 400000)
        native_build_number = random.randint(60000, 70000)
        payload = {
            "os": os_name,
            "browser": "Discord Client",
            "release_channel": "ptb",
            "client_version": discord_version, 
            "os_version": "10.0.26100",
            "os_arch": "x64",
            "app_arch": "x64",
            "system_locale": "fr", 
            "has_client_mods": False,
            "browser_user_agent": user_agent, 
            "browser_version": electron_version,
            "os_sdk_version": "26100",
            "client_build_number": client_build_number,
            "native_build_number": native_build_number, 
            "client_event_source": None
        }
        return base64.b64encode(json.dumps(payload).encode()).decode()

    @debug
    def get_user_id(self) -> int | None:
        response = self.session.get('https://ptb.discord.com/api/v9/users/@me')
        debug_response(response)
        if response.status_code == 200:
            return int(response.json().get('id'))
        elif response.status_code == 401:
            return 401
        else:
            log.failure(f"Failed to get user ID: {response.text}, {response.status_code}")
        return None
    
    @debug
    def create_dm_channel(self, target_id: str) -> int | None:
        self.session.headers["referer"] = "https://ptb.discord.com/channels/@me"
        self.session.headers["x-context-properties"] = "eyJsb2NhdGlvbiI6IlVzZXIgUHJvZmlsZSJ9="
        payload = {'recipients': [target_id]}
        response = self.session.post('https://ptb.discord.com/api/v9/users/@me/channels', json=payload)
        debug_response(response)
        if response.status_code == 200:
            channel_id = int(response.json().get('id'))
            return channel_id
        elif response.status_code == 403:
            log.warning(f"Setup: Failed to create DM with {target_id}: 403 Forbidden. Check privacy/blocks.")
            return None
        elif response.status_code == 429:
            retry_after = response.json().get('retry_after', 1)
            log.warning(f"Setup: Rate limited creating DM with {target_id}. Retrying after {retry_after}s")
            time.sleep(retry_after)
            return self.create_dm_channel(target_id)
        else:
            log.warning(f"Setup: Failed to create DM with {target_id}: Status {response.status_code}")
            return None

    @debug
    def leave_group(self, group_id: str) -> bool:
        response = self.session.delete(f'https://ptb.discord.com/api/v9/channels/{group_id}', params={'silent': 'true'})
        debug_response(response)
        if response.status_code == 200:
            return True
        elif response.status_code == 429:
            retry_after = response.json().get('retry_after', 1)
            log.warning(f"Rate limited leaving/closing channel {group_id}. Retrying after {retry_after}s")
            time.sleep(retry_after)
            return self.leave_group(group_id)
        else:
            log.failure(f"Failed to leave/close channel {group_id}: {response.text}, {response.status_code}")
            return False

    @debug
    def send_message(self, channel_id: str, message: str) -> bool:
        nonce = str(random.randint(10**18, 10**19))
        self.session.headers["referer"] = f"https://ptb.discord.com/channels/@me/{channel_id}"
        json_data = {
            'mobile_network_type': 'unknown',
            'content': message,
            'nonce': nonce,
            'tts': False,
            'flags': 0,
        }
        response = self.session.post(f'https://ptb.discord.com/api/v9/channels/{channel_id}/messages', json=json_data)
        debug_response(response)
        if response.status_code == 200:
            return True
        if response.status_code == 429:
            retry_after = response.json().get('retry_after', 1)
            log.warning(f"Rate limited while sending message to {channel_id}. Retrying after {retry_after}s")
            time.sleep(retry_after)
            return self.send_message(channel_id, message)
        else:
            log.failure(f"Failed to send message to {channel_id}: {response.text}, {response.status_code}")
            return False

    @debug
    def create_invite_link(self, group_id: str) -> str | None:
        self.session.headers["x-context-properties"] = "eyJsb2NhdGlvbiI6Ikdyb3VwIERNIEludml0ZSBDcmVhdGUifQ==",
        json_data = {
            'max_age': 86400,
        }
        response = self.session.post(
            f'https://ptb.discord.com/api/v9/channels/{group_id}/invites',
            json=json_data,
        )
        debug_response(response)
        if response.status_code == 200:
            invite_code = response.json().get('code')
            return invite_code
        else:
            log.failure(f"Failed to create invite link: {response.text}, {response.status_code}")
        return None
    
    @debug
    def join_group(self, invite_code: str) -> bool:
        json_data = {
            'session_id': str(uuid.uuid4()).replace("-", ""),
        }
        response = self.session.post(f'https://ptb.discord.com/api/v9/invites/{invite_code}', json=json_data)
        if response.status_code == 200:
            return True
        else:
            log.failure(f"Failed to join group: {response.text}, {response.status_code}")

def spam_user(token: str, messages_to_send: int, target_ids: list, misc: Miscellaneous) -> bool:
    proxies = misc.get_proxies()
    dm_manager = GroupCreator(misc, token, proxies)
    user_id = dm_manager.get_user_id()
    if user_id == 401:
        log.failure(f"Invalid token: {token[:30]}...")
        return False
    elif not user_id:
        log.failure(f"Failed to get user ID for token {token[:30]}...")
        return False
    log.info(f"Starting infinite spam loop for token {token[:30]}... User ID: {user_id}")
    while True:
        try:
            start_time = time.time()
            dm_channels_info = []
            for target_id in target_ids:
                channel_id = dm_manager.create_dm_channel(target_id)
                if channel_id:
                    log.success(f"Established DM channel {channel_id} with target {target_id} using token {token[:30]}...")
                    dm_channels_info.append(channel_id)
                else:
                    log.warning(f"Could not establish DM with target {target_id} for token {token[:30]}..., skipping.")
                    continue
            for channel_id in dm_channels_info:
                log.info(f"Processing DM channel {channel_id} for token {token[:30]}...")
                if config["data"].get("messages"):
                    num_message_loops = config['data'].get('messages_to_send', 1)
                    message_list = config["data"]["messages"]
                    total_messages_to_send_per_channel = len(message_list) * num_message_loops
                    message_sent_count = 0
                    for i in range(num_message_loops):
                        for message in message_list:
                            message_sent_count += 1
                            if dm_manager.send_message(channel_id, message):
                                log.success(f"Token {token[:30]}... {message_sent_count}/{total_messages_to_send_per_channel} Message sent to DM channel {channel_id}: {message[:20]}...")
                            else:
                                log.failure(f"Token {token[:30]}... Failed to send message {message_sent_count}/{total_messages_to_send_per_channel} to DM channel {channel_id}.")
                                break
                        else:
                            continue
                        break
            log.message("Discord", f"Completed one cycle for token {token[:30]}... Restarting loop", start_time, time.time())
        except KeyboardInterrupt:
            log.info(f"Process interrupted by user for token {token[:30]}... Exiting thread.")
            return True
        except Exception as e:
            log.failure(f"Error during spam loop for token {token[:30]}...: {e}")
            import traceback
            traceback.print_exc()
            return False

def main() -> None:
    try:
        Misc = Miscellaneous()
        Banner = Home("DM Spammer", align="center", credits="discord.cyberious.xyz")
        Banner.display()
        target_ids = config['data'].get('targets')
        if not target_ids:
            log.failure("No target IDs found in config.toml under [data].targets. Exiting.")
            return
        with open("input/tokens.txt", 'r') as f:
            tokens = [line.strip() for line in f if line.strip()]
        if not tokens:
            log.warning("Input token file is empty. Exiting.")
            return
        num_tokens = len(tokens)
        requested_thread_count = config['dev'].get('Threads', 1)
        messages_to_send = config['data'].get('messages_to_send', 1)
        actual_thread_count = max(requested_thread_count, num_tokens)
        if actual_thread_count != requested_thread_count:
            log.warning(f"Requested thread count ({requested_thread_count}) is less than token count ({num_tokens}).")
            log.warning(f"Adjusting thread count to match token count: {num_tokens}")
        log.info(f"Requested threads: {requested_thread_count}, Actual threads to run: {actual_thread_count}, Tokens available: {num_tokens}")
        tasks_to_submit = []
        base_threads_per_token = actual_thread_count // num_tokens
        remainder_threads = actual_thread_count % num_tokens
        debug(f"Distributing {actual_thread_count} threads across {num_tokens} tokens.")
        if remainder_threads > 0:
             debug(f"Each token gets {base_threads_per_token} thread(s). The first {remainder_threads} token(s) get an additional thread.")
        else:
             debug(f"Each token gets {base_threads_per_token} thread(s).")
        current_task_count = 0
        for i, token in enumerate(tokens):
            threads_for_this_token = base_threads_per_token
            if i < remainder_threads:
                threads_for_this_token += 1
            for _ in range(threads_for_this_token):
                if current_task_count < actual_thread_count:
                    tasks_to_submit.append((token, messages_to_send, target_ids, Misc))
                    current_task_count += 1
        actual_thread_count = len(tasks_to_submit)
        log.info(f"Final task count matches adjusted thread count: {actual_thread_count}")
        ctypes.windll.kernel32.SetConsoleTitleW(f'discord.cyberious.xyz | Running {actual_thread_count} worker threads...')
        with ThreadPoolExecutor(max_workers=actual_thread_count) as executor:
            future_to_token = {executor.submit(spam_user, *task_args): task_args[0] for task_args in tasks_to_submit}
            log.info(f"Launched {len(future_to_token)} worker threads. Press Ctrl+C to stop.")
            for future in as_completed(future_to_token):
                token = future_to_token[future]
                try:
                    result = future.result()
                    if result is False:
                         log.warning(f"Thread for token {token[:30]}... exited (likely invalid token or error).")
                    elif result is True:
                         log.info(f"Thread for token {token[:30]}... exited cleanly (Ctrl+C).")
                except Exception as e:
                    log.failure(f"Thread for token {token[:30]}... encountered an error: {e}")
                    import traceback
                    traceback.print_exc()
    except KeyboardInterrupt:
        log.info("Process interrupted by user. Exiting...")
    except Exception as e:
        log.failure(f"An unexpected error occurred in main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()