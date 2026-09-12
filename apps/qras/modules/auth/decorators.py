# from django.shortcuts import redirect


# def permission_required(module_code, action='read'):
#     """
#     Guards a view by module permission.
#     - Admins (role.name == 'Admin') always pass.
#     - Others must have the matching RolePermission flag set to True.
#     """
#     def decorator(view_func):
#         def wrapper(request, *args, **kwargs):
#             if not request.user.is_authenticated:
#                 return redirect('login')

#             role = request.user.role

#             if role is None:
#                 return redirect('error-401')

#             if role.name == 'Admin':
#                 return view_func(request, *args, **kwargs)

#             perm = role.permissions.filter(module__code=module_code).first()

#             action_map = {
#                 'create': getattr(perm, 'can_create', False),
#                 'read':   getattr(perm, 'can_read',   False),
#                 'update': getattr(perm, 'can_update',  False),
#                 'delete': getattr(perm, 'can_delete',  False),
#             }

#             if perm and action_map.get(action, False):
#                 return view_func(request, *args, **kwargs)

#             return redirect('error-401')
#         return wrapper
#     return decorator


# # Backward-compat shim — keeps existing @role_required('admin') calls working
# # during transition. Remove once all views are migrated to permission_required.
# '''
# The role_required shim means zero existing views break right now. 
# They keep working as-is — role_required('admin') still matches the Admin role by name.

# When you want to open a view to other roles later, you swap its decorator from:

# python@method_decorator([role_required('admin')], name='dispatch')

# to:
# python@method_decorator([permission_required('module_code', 'read')], name='dispatch')

# '''
# def role_required(role):
#     def decorator(view_func):
#         def wrapper(request, *args, **kwargs):
#             if not request.user.is_authenticated:
#                 return redirect('login')
#             user_role = request.user.role
#             if user_role is None:
#                 return redirect('error-401')
#             if user_role.name.lower() == role.lower():
#                 return view_func(request, *args, **kwargs)
#             return redirect('error-401')
#         return wrapper
#     return decorator