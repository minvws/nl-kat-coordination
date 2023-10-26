# Rocky

Note that Rocky does not support auto-generated environment documentation.

The following places contain more information about which settings Rocky supports:
- [rocky/rocky/settings.py](https://github.com/minvws/nl-kat-coordination/blob/main/rocky/rocky/settings.py)
- [.env-defaults](https://github.com/minvws/nl-kat-coordination/blob/main/.env-defaults)
- [.env-dist](https://github.com/minvws/nl-kat-coordination/blob/main/.env-dist)
- [Django docs about settings](https://docs.djangoproject.com/en/4.2/topics/settings/)
- [Django complete settings reference](https://docs.djangoproject.com/en/4.2/ref/settings/)


## Email forwarding

[rocky/rocky/settings.py](https://github.com/minvws/nl-kat-coordination/blob/main/rocky/rocky/settings.py#L102-L122) allows you to set the email settings for your OpenKAT install. Errors will be written to Rockys email logs as specified in the ENV file.
