def ui_settings(request):
    data = {
        'theme': 'auto',
        'dark_mode': False,
        'font_size': 'md',
        'reduced_motion': False,
        'high_contrast': False,
        'compact_mode': False,
        'language': 'en',
    }
    if request.user.is_authenticated and hasattr(request.user, 'studentprofile'):
        s = getattr(request.user.studentprofile, 'settings', None)
        if s:
            data.update({
                'theme': s.theme or 'auto',
                'dark_mode': s.dark_mode,
                'font_size': s.font_size or 'md',
                'reduced_motion': s.reduced_motion,
                'high_contrast': s.high_contrast,
                'compact_mode': s.compact_mode,
                'language': s.language or 'en',
            })
    return {'ui_settings': data}

def user_ui_settings(request):
    # default
    ctx = {'dark_mode': False}
    if request.user.is_authenticated and hasattr(request.user, 'studentprofile'):
        settings_obj = getattr(request.user.studentprofile, 'settings', None)
        if settings_obj:
            ctx['dark_mode'] = bool(settings_obj.dark_mode)
    return ctx
