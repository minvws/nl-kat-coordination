Login & registration
====================

Registration
------------

As an administrator, you can register new users on the "Members page". Read more about this page here :doc:`../navigation/members`.
If you are a normal user and you want to register to OpenKAT, please contact your administrator.


Login
-----

Once you have got your account credentials, you should be able to log in with the given username and password.


Reset password
--------------

If you want to change your password, click on the profile menu on the top right and go to "Profile".
Then press "Reset password". After entering your email address, a reset link will be send to this email address.


Two-factor authentication (2FA)
-------------------------------

Once you login you will see the screen for setting up two-factor authentication. You have to scan the QR code with an authenticator application on your phone, the application on your phone will generate a token that you have to type in as a response. Every time you want to login, you have to enter your username, password and 2FA token. You can disable 2FA in the `.env` file if necessary.


.. image:: img/00-onboarding-qr-code.png
  :alt: Setting up two-factor authentication.

Once you have successfully setup 2FA you will see the following screen.

.. image:: img/00-onboarding-qr-success.png
  :alt: Successful setup of two-factor authentication.

After this, continue to the onboarding. The onboarding starts with the registration process, which let's you create your very first organization.
