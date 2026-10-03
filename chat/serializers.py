from rest_framework import serializers

from listings.models import Listing
from users.serializers import PublicUserSerializer

from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender = PublicUserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ("id", "conversation", "sender", "text", "is_read", "created_at")
        read_only_fields = ("conversation", "is_read")


class ConversationSerializer(serializers.ModelSerializer):
    buyer = PublicUserSerializer(read_only=True)
    seller = PublicUserSerializer(read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Conversation
        fields = (
            "id", "listing", "listing_title", "buyer", "seller",
            "last_message", "unread_count", "created_at", "updated_at",
        )

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        return MessageSerializer(msg).data if msg else None


class StartConversationSerializer(serializers.Serializer):
    listing = serializers.PrimaryKeyRelatedField(queryset=Listing.objects.filter(is_active=True))
    text = serializers.CharField(required=False, allow_blank=True, max_length=4000)
