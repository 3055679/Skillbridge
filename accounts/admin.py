from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import redirect
from .models import User, StudentProfile, EmployerProfile, Skill, Education, Experience, PortfolioItem, PortfolioImage, PortfolioVideo

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_student', 'is_employer', 'date_joined')
    list_filter = ('is_student', 'is_employer', 'date_joined')
    search_fields = ('username', 'email')

class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('admin_thumbnail', 'user_info', 'university', 'student_id_verified', 'approve_button')
    list_filter = ('student_id_verified', 'country')
    search_fields = ('user__username', 'user__email', 'university')
    readonly_fields = ('admin_thumbnail',)
    raw_id_fields = ('user',)
    actions = ['approve_profiles']

    fieldsets = (
        (None, {
            'fields': ('user', 'admin_thumbnail')
        }),
        ('Profile Information', {
            'fields': ('profile_picture', 'bio', 'phone_number', 'university', 'country')
        }),
        ('Verification', {
            'fields': ('student_id_document', 'student_id_verified')
        })
    )

    def user_info(self, obj):
        if obj.user:
            return f"{obj.user.username} ({obj.user.email})"
        return "No user"
    user_info.short_description = 'User'

    def admin_thumbnail(self, obj):
        if obj.profile_picture:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%; object-fit: cover;" />', obj.profile_picture.url)
        return "No Image"
    admin_thumbnail.short_description = 'Profile Picture'

    def approve_button(self, obj):
        if obj.student_id_document and not obj.student_id_verified:
            return format_html(
                '<a class="button" href="{}">Approve</a>',
                reverse('admin:approve_student', args=[obj.pk])
            )
        elif obj.student_id_verified:
            return "Approved"
        return "No ID Uploaded"
    approve_button.short_description = 'Verification Status'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/approve/', self.admin_site.admin_view(self.approve_profile),
                 name='approve_student'),
        ]
        return custom_urls + urls

    def approve_profile(self, request, pk):
        profile = StudentProfile.objects.get(pk=pk)
        profile.student_id_verified = True
        profile.save()
        self.message_user(request, f"Approved student ID for {profile.user.username}")
        return redirect('admin:accounts_studentprofile_changelist')

    def approve_profiles(self, request, queryset):
        queryset.update(student_id_verified=True)
        self.message_user(request, f"Approved {queryset.count()} student profiles")
    approve_profiles.short_description = "Mark selected as verified"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if request.user.is_superuser:
            form.base_fields['bio'].required = False
            form.base_fields['phone_number'].required = False
            form.base_fields['university'].required = False
            form.base_fields['profile_picture'].required = False
        return form

    def save_model(self, request, obj, form, change):
        if '_approve' in request.POST:
            obj.student_id_verified = True
            obj.save()
            self.message_user(request, "Student approved without profile completion")
        else:
            super().save_model(request, obj, form, change)

class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ('admin_thumbnail', 'user_info', 'company_name', 'is_approved')
    list_filter = ('is_approved',)
    search_fields = ('user__username', 'user__email', 'company_name')
    raw_id_fields = ('user',)

    def user_info(self, obj):
        if obj.user:
            return f"{obj.user.username} ({obj.user.email})"
        return "No user"
    user_info.short_description = 'User'

    def admin_thumbnail(self, obj):
        if obj.company_logo:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: contain;" />', obj.company_logo.url)
        return "No Logo"
    admin_thumbnail.short_description = 'Logo'

admin.site.register(User, UserAdmin)
admin.site.register(StudentProfile, StudentProfileAdmin)
admin.site.register(EmployerProfile, EmployerProfileAdmin)
admin.site.register(Skill)
admin.site.register(Education)
admin.site.register(Experience)
admin.site.register(PortfolioItem)
admin.site.register(PortfolioImage)
admin.site.register(PortfolioVideo)