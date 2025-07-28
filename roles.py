class Role:
    def __init__(self):
        self.permissions = set()

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

class SuperAdmin(Role):
    def __init__(self):
        super().__init__()
        self.permissions = {
            "register_channel", 
            "set_admin", 
            "set_registrator", 
            "link_channel", 
            "unlink_channel", 
            "remove_channel_registration", 
            "set_registrator",
            "remove_admin",
            "remove_registrator",
            "can't_be_admin",
            "can't_be_registrator",
            "superadmin_only",
            "admin_only"
            }

class Admin(Role):
    def __init__(self):
        super().__init__()
        self.permissions = {
            "register_channel", 
            "set_registrator", 
            "link_channel", 
            "unlink_channel", 
            "remove_channel_registration", 
            "set_registrator",
            "remove_registrator",
            "can't_be_registrator",
            "admin_only"
            }

class Registrator(Role):
    def __init__(self):
        super().__init__()
        self.permissions = {
            "register_channel", 
            "link_channel", 
            "unlink_channel"
            }
