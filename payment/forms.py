from django import forms
from .models import TaskAssignment, Feedback, TaskSubmission

class TaskAssignmentForm(forms.ModelForm):
    class Meta:
        model = TaskAssignment
        fields = ['task_description', 'due_date']
        widgets = {
            'task_description': forms.Textarea(attrs={'data-bs-toggle': 'tooltip', 'title': 'Describe the task or duties'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'data-bs-toggle': 'tooltip', 'title': 'Optional due date'}),
        }

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['task_given', 'performance', 'rating']
        widgets = {
            'task_given': forms.Textarea(attrs={'data-bs-toggle': 'tooltip', 'title': 'What was the task assigned?'}),
            'performance': forms.Textarea(attrs={'data-bs-toggle': 'tooltip', 'title': 'How did the student perform?'}),
            'rating': forms.Select(choices=[(i, i) for i in range(1, 6)], attrs={'data-bs-toggle': 'tooltip', 'title': 'Rate out of 5'}),
        }

class TaskSubmissionForm(forms.ModelForm):
    class Meta:
        model = TaskSubmission
        fields = ['work_file', 'description']
        widgets = {
            'work_file': forms.FileInput(attrs={'data-bs-toggle': 'tooltip', 'title': 'Upload your completed work (e.g., PDF, code, image)'}),
            'description': forms.Textarea(attrs={'data-bs-toggle': 'tooltip', 'title': 'Describe tools, technologies, or details (e.g., Python, Figma, color contrast used)'}),
        }