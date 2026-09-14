from qras.modules.features.clock_offset.utils import get_clock_offset
from qras.models.access import Module


def user_permissions(request):
    if not request.user.is_authenticated:
        return {'user_perms': {}}

    role = getattr(request.user, 'role', None)
    if not role:
        return {'user_perms': {}}

    if role.name == 'Admin':
        perms = {
            m.code: {'create': True, 'read': True, 'update': True, 'delete': True}
            for m in Module.objects.all()
        }
        return {'user_perms': perms}

    perms = {}
    for rp in role.permissions.select_related('module').all():
        perms[rp.module.code] = {
            'create': rp.can_create,
            'read':   rp.can_read,
            'update': rp.can_update,
            'delete': rp.can_delete,
        }
    return {'user_perms': perms}


def clock_offset(request):
    return {
        'CLOCK_OFFSET_MINUTES': get_clock_offset()
    }