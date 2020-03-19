'''
A channel layer is a kind of communication system. It allows multiple consumer instances to talk with each other, and with other parts of Django.

A channel layer provides the following abstractions:

A channel is a mailbox where messages can be sent to. Each channel has a name. Anyone who has the name of a channel can send a message to the channel.
A group is a group of related channels. A group has a name. Anyone who has the name of a group can add/remove a channel to the group by name and send a message to all channels in the group. It is not possible to enumerate what channels are in a particular group.
Every consumer instance has an automatically generated unique channel name, and so can be communicated with via a channel layer.

In our chat application we want to have multiple instances of ChatConsumer in the same room communicate with each other. To do that we will have each ChatConsumer add its channel to a group whose name is based on the room name. That will allow ChatConsumers to transmit messages to all other ChatConsumers in the same room.
'''
from django.contrib.auth import get_user_model
import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from chat.models import Message
# from django.contrib.auth.models import User

User = get_user_model()

class ChatConsumer(WebsocketConsumer):
    commands = {
        'fetch_messages': 'fetch_messages',
        'new_message': 'new_message'
    }

    def fetch_messages(self, data):
        messages = Message.objects.all()
        # Message.last_10_messages()
        content = {
            'command': 'messages',
            'chat_messages': self.messages_to_json(messages)
        }
        # print("the messages retrieved: {}".format(messages))
        self.send_message(content)

    def messages_to_json(self, messages):
        result = []
        for message in messages:
            result.append(self.message_to_json(message))
            print("Result : {}".format(self.message_to_json(message)))
        return result

    def message_to_json(self, message):
        return {
            'author': message.author.username,
            'content': message.content,
            'timestamp': str(message.timestamp)
        }

    def new_message(self, data):
        author = data['from']
        author_user = User.objects.get(username=author)
        print("the user: {}".format(author_user.username))
        message = Message.objects.create(
            author = author_user,
            content = data['message']
        )
        print("author: {} data: {}".format(author, data))
        # print("the message : {}".format(message))
        content = {
            'command': 'new_message',
            'chat_message': self.message_to_json(message)
        }
        return self.send_chat_message(content)

    def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        print("The room is {}".format(self.room_name))
        self.room_group_name = 'chat_%s' % self.room_name

        # Join room group
        #The async_to_sync(…) wrapper is required because ChatConsumer is a synchronous WebsocketConsumer but it is calling an asynchronous channel layer method. (All channel layer methods are asynchronous.)
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    def receive(self, text_data):
        data = json.loads(text_data)
        # self.commands[data['command']](self, data)
        if data['command'] == 'fetch_messages':
            self.fetch_messages(data)
        elif data['command'] == 'new_message':
            self.new_message(data)

    def send_chat_message(self, message):
        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'chat_message',#method to be called when message is added to the group
                'message': message
            }
        )

    def send_message(self, message):
        self.send(text_data=json.dumps(message))


    # Receive message from room group
    def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        self.send(text_data=json.dumps(message))