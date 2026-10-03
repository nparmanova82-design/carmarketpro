from django.conf import settings
from django.db import models


class Conversation(models.Model):
    """Диалог покупателя и продавца по конкретному объявлению."""

    listing = models.ForeignKey("listings.Listing", on_delete=models.CASCADE, related_name="conversations")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="buyer_conversations")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seller_conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [models.UniqueConstraint(fields=["listing", "buyer"], name="unique_conversation")]
        verbose_name = "диалог"
        verbose_name_plural = "диалоги"

    def __str__(self):
        return f"{self.buyer} ↔ {self.seller} ({self.listing})"

    def has_participant(self, user):
        return user.pk in (self.buyer_id, self.seller_id)


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    text = models.TextField("сообщение", max_length=4000)
    is_read = models.BooleanField("прочитано", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        verbose_name = "сообщение"
        verbose_name_plural = "сообщения"
