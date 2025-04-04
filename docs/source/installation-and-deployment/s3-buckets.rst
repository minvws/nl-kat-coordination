==========
S3 buckets
==========

OpenKAT stores most of its data in integrated databases. However, if you
have access to S3 storage buckets, you may prefer using those instead.
This manual helps you to setup OpenKAT to make use of your S3 buckets.

Enabling S3 buckets for Bytes
=============================

When you want to activate OpenKAT's S3 functionalities you need to have
an existing S3 service running which is reachable by Bytes. When
this service is up and running, you need to add the following three
environment variables to the ``.env`` of the machine that is running
Bytes

-  **AWS_ACCESS_KEY_ID**: The id of the key that can access your S3
   storage.
-  **AWS_SECRET_ACCESS_KEY**: The secret of the before mentioned key
-  **AWS_ENDPOINT_URL**: The URL that describes where the S3 storage is
   located.

Using these environment variables OpenKAT can have access to the S3
service. OpenKAT requires at least one additional environment variable
to determine the name of the S3 bucket it should create or use.

S3 bucket names
===============

OpenKAT offers 2 methods of naming the buckets. The first one is done by
directly adding the environment variable ``S3_BUCKET`` with a name that
complies with the `bucket naming rules of
AWS <https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html>`__.
This will make OpenKAT throw all of Bytes' data into the bucket
with this name.

The second method allows you to set a prefix for bucket names, which
will be followed by the organization's name. For example, if you set the
prefix to ``cyn-``, OpenKAT will create buckets named ``cyn-org`` and
``cyn-org2`` for organizations ``org`` and ``org2``. This can be done by
adding 2 more environment variables:

-  **BUCKET_PER_ORG**: This has to be set to ``true`` to tell OpenKAT
   you want to use a prefix.
-  **S3_BUCKET_PREFIX**: The name of the prefix you want to use. Make
   sure that this prefix also follows the `bucket naming rules of
   AWS <https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html>`__.

After either of these methods have been added files generated by
Bytes should be seen inside the S3 buckets.

.. warning::
   Using this method means that the previously saved files saved by
   Bytes are not accessible anymore. Keep this in mind when enabling S3
   buckets.

   And vice versa when disabling S3 buckets.
