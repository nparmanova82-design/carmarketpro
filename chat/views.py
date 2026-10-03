from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer, StartConversationSerializer


class ConversationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Чат покупатель ↔ продавец.
    Клиент получает новые сообщения через `GET /chats/{id}/messages/?after=<id>` (polling).
    """

    serializer_class = ConversationSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_backends = ()

    queryset = Conversation.objects.none()  # for schema generation

    def get_queryset(self):
        user = self.request.user
        return (
            Conversation.objects.filter(Q(buyer=user) | Q(seller=user))
            .select_related("listing", "buyer", "seller")
            .annotate(unread_count=Count("messages", filter=Q(messages__is_read=False) & ~Q(messages__sender=user)))
        )

    @extend_schema(
        summary="Начать диалог по объявлению (или вернуть существующий)",
        request=StartConversationSerializer,
        responses=ConversationSerializer,
    )
    def create(self, request):
        serializer = StartConversationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = serializer.validated_data["listing"]
        if listing.seller_id == request.user.pk:
            raise ValidationError({"listing": "Нельзя написать самому себе."})

        conversation, created = Conversation.objects.get_or_create(
            listing=listing, buyer=request.user, defaults={"seller": listing.seller}
        )
        text = serializer.validated_data.get("text")
        if text:
            Message.objects.create(conversation=conversation, sender=request.user, text=text)
            conversation.save(update_fields=["updated_at"])

        conversation = self.get_queryset().get(pk=conversation.pk)
        return Response(
            self.get_serializer(conversation).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(summary="Сообщения диалога / отправить сообщение", request=MessageSerializer, responses=MessageSerializer(many=True))
    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        conversation = self.get_object()

        if request.method == "POST":
            serializer = MessageSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(conversation=conversation, sender=request.user)
            Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        qs = conversation.messages.select_related("sender")
        after = request.query_params.get("after")
        if after and after.isdigit():
            qs = qs.filter(pk__gt=int(after))
        # opening the chat marks the other side's messages as read
        conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

        page = self.paginate_queryset(qs)
        return self.get_paginated_response(MessageSerializer(page, many=True).data)

    @extend_schema(summary="Общее число непрочитанных сообщений")
    @action(detail=False)
    def unread(self, request):
        count = (
            Message.objects.filter(is_read=False)
            .filter(Q(conversation__buyer=request.user) | Q(conversation__seller=request.user))
            .exclude(sender=request.user)
            .count()
        )
        return Response({"unread": count})
