"""Ayrıcalıklı hesap ucunda yetki denetimi servis yetkisinden önce gelmeli."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('irp_sunucu',Path(__file__).parents[1]/'sunucu.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AccountTests(unittest.TestCase):
    def test_no_token(self):
        with self.assertRaises(PermissionError):
            module.hesap_isle('',{'kisi':'K041','sifre':'123456','islem':'sifirla'})

    def test_denied_never_uses_service(self):
        calls=[]
        def remote(method,path,body,admin):
            calls.append(admin)
            raise PermissionError()
        with self.assertRaises(PermissionError):
            module.hesap_isle('Bearer synthetic',{'kisi':'K041','sifre':'123456','islem':'sifirla'},
                             env={'IRP_SB_TEST_URL':'https://example.invalid'},remote=remote)
        self.assertEqual(calls,[False])

    def test_wrong_person_never_uses_service(self):
        def remote(method,path,body,admin):
            self.assertFalse(admin)
            return {'deger':[]}
        with self.assertRaises(ValueError):
            module.hesap_isle('Bearer synthetic',{'kisi':'K041','sifre':'123456','islem':'ac'},
                             env={'IRP_SB_TEST_URL':'https://example.invalid'},remote=remote)

    def test_create_checks_user_before_admin_and_maps_person(self):
        calls=[]
        statements=[]
        class Result:
            def fetchone(self):return None
        class Connection:
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def execute(self,query,args):statements.append((query,args));return Result()
        def remote(method,path,body,admin):
            calls.append((method,path,admin))
            if not admin:return {'deger':[{'kisi':'K041','hesap_var':False}]}
            return {'id':'synthetic-auth-id'}
        result=module.hesap_isle('Bearer synthetic',{'kisi':'K041','sifre':'654321','islem':'ac'},
            env={'IRP_SB_TEST_URL':'https://example.invalid','IRP_SB_TEST_DB':'synthetic'},
            remote=remote,connector=lambda *a,**k:Connection())
        self.assertTrue(result['ok'])
        self.assertFalse(calls[0][2]);self.assertTrue(calls[1][2])
        self.assertEqual(statements[-1][1],('synthetic-auth-id','K041'))

    def test_reset_uses_mapped_auth_person(self):
        calls=[]
        class Result:
            def fetchone(self):return ('synthetic-auth-id',)
        class Connection:
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def execute(self,*_):return Result()
        def remote(method,path,body,admin):
            calls.append((method,path,admin))
            return {'deger':[{'kisi':'K041','hesap_var':True}]} if not admin else {}
        module.hesap_isle('Bearer synthetic',{'kisi':'K041','sifre':'654321','islem':'sifirla'},
            env={'IRP_SB_TEST_URL':'https://example.invalid','IRP_SB_TEST_DB':'synthetic'},
            remote=remote,connector=lambda *a,**k:Connection())
        self.assertEqual(calls[-1],('PUT','/auth/v1/admin/users/synthetic-auth-id',True))

    def test_bad_password_rejected_before_remote(self):
        with self.assertRaises(ValueError):
            module.hesap_isle('Bearer synthetic',{'kisi':'K041','sifre':'abc','islem':'ac'})


if __name__=='__main__':
    unittest.main()
