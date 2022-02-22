Jupyterhub README

=====

Welcome to the Fourfront Jupyterhub!

NOTE: This is a BETA server under active development and features may change without notice.

This is server that spawns Jupyter notebooks for users registered with Fourfront, the 4DN Data Portal. Here, you can run analyses seamlessly with Foufront data in a pre-configured environment. Each user gets his or her own workspace, so files saved are private to you. We have also supplied a number of examples files that will appear automatically in the `examples` directory. Please email DCIC if you would like to add other examples. 

Please note that changes to the example files will be overridden upon restarting. If you would like to persist your changes, save the file under a different name. In general it is recommended to use the root folder for your work. To trigger a restart, click "Control Panel" in the top right of the page and then click "Stop My Server". Servers are shut down periodically after some time has passed with no interaction.

We have also provided a Python module for each programmatic access to Fourfront. It is called `jh_utils` and can be easily imported using `from dcicutils import jh_utils`. The example files show how using this module makes working with 4DN data easy.

The autosave feature of Jupyterhub is disabled for all files; as such, please remember to save your work before closing a file.

THINGS TO KNOW ABOUT USING THE HUB:
- You may periodically get a message while using your notebook saying "Notebook changed. The notebook file has changed on disk..." NEVER click "Reload", as that may cause you to lose your progress. Instead choose "Overwrite" (saves your notebook) or "Cancel."
- Your server will be shut down automatically after an hour of inactivity.
- Your server is limited to 2G of memory usage.

KNOWN ISSUES ON THE HUB:
- Iteratively writing large files to the Jupyterhub will cause to it be slow/unresponsive.

