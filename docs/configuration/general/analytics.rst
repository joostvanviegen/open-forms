.. _configuration_general_analytics:

Analytics
=========

By default, Open Forms does not enable any form of external data analytics
tools. However, you can enable these tools within Open Forms. Below, we list
the integration possibilities within Open Forms.

.. warning::

    If you enable external data analytics tools, you **need** to set up a proper
    :ref:`cookie policy <configuration_general_cookies>` in accordance with
    the `GDPR`_ and your local privacy authority.

    Also, these data analytics tools will **only work** if the user allowed
    these cookies. If you do not set up cookies, these tools will simply not
    work because the user never allowed their cookies.

.. _`GDPR`: https://gdpr.eu/


Supported tools
---------------

The following tools are supported out of the box with Open Forms.

.. image:: _assets/admin_analytics_settings.png


* `Google Analytics <https://marketingplatform.google.com/about/analytics/>`__
* `Google Tag Manager <https://marketingplatform.google.com/about/tag-manager/>`__
* `Matomo (Piwik) <https://matomo.org/>`__ (cloud and on-premise support)
* `Piwik PRO  <https://piwikpro.nl/>`__
* `SiteImprove <https://siteimprove.com/en/analytics/>`__

.. note::

    Matomo was formerly known as Piwik. Do not confuse Piwik with Piwik PRO,
    which is a different product from a different company.


Configuration
-------------

1. Please make sure there's an analytics cookie group available. You can check
   or configure this via :ref:`configure_cookies`.

2. Navigate to **Configuration** > **General configuration**.

3. Scroll down to **Analytics: ...** and configure one of the supported data
   analytics tools.

4. Scroll down more to **Privacy & cookies**

5. In **Analytics cookie consent group** select the appropriate *cookie group*
   configured in step 1.

   .. warning::

       If you don't do this, the data analytics tools will not work!

6. Scroll to the bottom and click **Save**.

Content Security Policy (CSP)
-----------------------------

Piwik PRO
"""""""""

* Required to enable Piwik PRO's nonce mechanism: ``script-src``.

* Required to load all necessary assets from Piwik PRO's Tag Manager: ``img-src``, ``font-src`` and ``style-src``.

* Required if your website is GDPR compliant: ``connect-src``, ``style-src`` and ``img-src``.

Example:

.. code-block:: text

    Content-Security-Policy: default-src 'self';
                             script-src  'self' client.piwik.pro 'nonce-nceIOfn39fn3e9h3sd';
                             connect-src 'self' client.containers.piwik.pro client.piwik.pro;
                             img-src     'self' client.containers.piwik.pro client.piwik.pro;
                             font-src    'self' client.containers.piwik.pro;
                             style-src   'self' client.containers.piwik.pro 'nonce-nceIOfn39fn3e9h3sd';

Please refer to the `Piwik PRO CSP documentation`_ for more information.

.. _`Piwik PRO CSP documentation`: https://developers.piwik.pro/en/latest/tag_manager/content_security_policy.html
