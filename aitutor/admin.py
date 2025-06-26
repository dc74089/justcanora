from django.contrib import admin
from .models import Agent, Conversation, Message, AgentMessage, UserMessage, Assessment, AssessmentConversation


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ('name', 'language', 'description')
    readonly_fields = ('id',)


class MessageInline(admin.TabularInline):
    model = Message
    fields = ('role', 'message', 'time')
    readonly_fields = ('role', 'message', 'time')
    extra = 0
    can_delete = False
    show_change_link = True


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'agent', 'course_id', 'assignment_id', 'locked')
    search_fields = ('id',)
    list_filter = ('locked', 'agent')
    readonly_fields = ('id',)
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'role', 'short_message', 'time')
    list_filter = ('role', 'time')
    search_fields = ('message',)
    readonly_fields = ('id', 'time', 'role')

    def short_message(self, obj):
        return (obj.message[:75] + '...') if len(obj.message) > 75 else obj.message
    short_message.short_description = 'Message'


@admin.register(AgentMessage)
class AgentMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'agent', 'message_id', 'time')
    search_fields = ('message', 'message_id')
    list_filter = ('agent', 'time')
    readonly_fields = ('id', 'time', 'role')


@admin.register(UserMessage)
class UserMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'student', 'time')
    search_fields = ('message',)
    list_filter = ('time',)
    readonly_fields = ('id', 'time', 'role')


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'canvas_assignment_id')
    readonly_fields = ('id',)


@admin.register(AssessmentConversation)
class AssessmentConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'student', 'agent', 'assessment', 'credit_awarded', 'understanding_score')
    search_fields = ('id', 'feedback')
    list_filter = ('credit_awarded', 'agent', 'assessment')
    readonly_fields = ('id',)
    inlines = [MessageInline]
