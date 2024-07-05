import socket
import json
from threading import Thread
import flet as ft  # Assuming 'flet' library is correctly imported

TARGET_IP = "127.0.0.1"
TARGET_PORT = 8889

class ChatClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = (TARGET_IP, TARGET_PORT)
        self.sock.connect(self.server_address)
        self.tokenid = ""
        self.group_active = False
        self.group_name = ""
        self.group_messages = []

    def sendstring(self, string):
        try:
            self.sock.sendall(string.encode())
            receivemsg = ""
            while True:
                data = self.sock.recv(64)
                if data:
                    receivemsg = "{}{}".format(receivemsg, data.decode())
                    if receivemsg[-4:] == '\r\n\r\n':
                        return json.loads(receivemsg)
        except Exception as e:
            self.sock.close()
            print(f"Error: {e}")
            return {'status': 'ERROR', 'message': 'Failed to connect'}

    def login(self, username, password):
        string = "auth {} {} \r\n".format(username, password)
        result = self.sendstring(string)
        if result['status'] == 'OK':
            self.tokenid = result['tokenid']
            return "username {} logged in, token {} ".format(username, self.tokenid)
        else:
            return "Error, {}".format(result['message'])

    def sendmessage(self, usernameto="xxx", message="xxx"):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "send {} {} {} \r\n".format(self.tokenid, usernameto, message)
        result = self.sendstring(string)
        if result['status'] == 'OK':
            return "Message sent to {}".format(usernameto)
        else:
            return "Error, {}".format(result['message'])

    def inbox(self):
        if self.tokenid == "":
            return "Error, not authorized"
        string = "inbox {} \r\n".format(self.tokenid)
        result = self.sendstring(string)
        if result['status'] == 'OK':
            return "{}".format(json.dumps(result['messages'], indent=4))
        else:
            return "Error, {}".format(result['message'])

    def group_chat(self, groupname, update_ui_callback):
        if self.tokenid == "":
            return "Error, not authorized"

        self.group_active = True
        self.group_name = groupname

        # Start a thread to receive messages from the group
        Thread(target=self.receive_group_messages, args=(update_ui_callback,)).start()

        # Send join group message
        string = 'group {} {} origin \r\n'.format(self.tokenid, groupname)
        self.sock.sendall(string.encode())

        return "Joined group '{}'".format(groupname)

    def receive_group_messages(self, update_ui_callback):
        try:
            while self.group_active:
                data = self.sock.recv(1024).decode()
                if data:
                    print(f"Received group message: {data}")
                    self.group_messages.append(data)
                    update_ui_callback()
        except Exception as e:
            print(f"Error receiving group messages: {e}")

    def send_group_message(self, message):
        if self.group_name:
            string = 'groupmsg {} {} {} \r\n'.format(self.tokenid, self.group_name, message)
            self.sock.sendall(string.encode())

    def leave_group(self):
        self.group_active = False
        if self.group_name:
            string = 'groupmsg {} {} exit \r\n'.format(self.tokenid, self.group_name)
            self.sock.sendall(string.encode())
            self.group_name = ""
            return "Left group '{}'".format(self.group_name)
        return "Not in any group"

def main(page: ft.Page):
    page.title = "Chat Client"
    page.padding = 20
    page.scroll = ft.ScrollMode.ALWAYS

    client = ChatClient()

    # Login controls
    username_input = ft.TextField(label="Username")
    password_input = ft.TextField(label="Password", password=True)
    login_status = ft.Text()

    def login(e):
        username = username_input.value
        password = password_input.value
        response = client.login(username, password)
        login_status.value = response
        page.update()

    login_button = ft.ElevatedButton(text="Login", on_click=login)

    # Message sending controls
    recipient_input = ft.TextField(label="Recipient")
    message_input = ft.TextField(label="Message")
    send_status = ft.Text()

    def send_message(e):
        recipient = recipient_input.value
        message = message_input.value
        response = client.sendmessage(recipient, message)
        send_status.value = response
        page.update()

    send_button = ft.ElevatedButton(text="Send Message", on_click=send_message)

    # Inbox controls
    inbox_display = ft.Text()

    def show_inbox(e):
        response = client.inbox()
        inbox_display.value = response
        page.update()

    inbox_button = ft.ElevatedButton(text="Show Inbox", on_click=show_inbox)

    # Group chat controls
    group_name_input = ft.TextField(label="Group Name")
    group_chat_status = ft.Text()
    group_messages_display = ft.Column()

    def update_group_messages():
        group_messages_display.controls.clear()
        for msg in client.group_messages:
            group_messages_display.controls.append(ft.Text(msg))
        page.update()

    def start_group_chat(e):
        group_name = group_name_input.value
        response = client.group_chat(group_name, update_group_messages)
        group_chat_status.value = response
        page.update()

    def send_group_message(e):
        message = message_input.value
        client.send_group_message(message)
        message_input.value = ""
        page.update()

    def leave_group_chat(e):
        client.leave_group()
        group_chat_status.value = f"Left group '{client.group_name}'"
        client.group_messages.clear()
        update_group_messages()

    group_chat_button = ft.ElevatedButton(text="Start Group Chat", on_click=start_group_chat)
    group_message_input = ft.TextField(label="Message to Group")
    group_message_button = ft.ElevatedButton(text="Send to Group", on_click=send_group_message)
    group_leave_button = ft.ElevatedButton(text="Leave Group Chat", on_click=leave_group_chat)

    # Layout
    page.add(
        ft.Column([
            ft.Text("Login"),
            username_input,
            password_input,
            login_button,
            login_status,
            ft.Divider(),
            ft.Text("Send Message"),
            recipient_input,
            message_input,
            send_button,
            send_status,
            ft.Divider(),
            ft.Text("Inbox"),
            inbox_button,
            inbox_display,
            ft.Divider(),
            ft.Text("Group Chat"),
            group_name_input,
            group_chat_button,
            group_chat_status,
            group_messages_display,
            group_message_input,
            group_message_button,
            group_leave_button,
        ])
    )

ft.app(target=main)
