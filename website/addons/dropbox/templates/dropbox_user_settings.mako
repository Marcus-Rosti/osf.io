## Template for the "Dropbox" section in the "Configure Add-ons" panel
<div id='dropboxAddonScope' class='addon-settings scripted'>

    <h4 class="addon-title">
      <img class="addon-icon" src="${addon_icon_url}"></img>
        Dropbox
        <!-- Delete Access Token Button -->
        <small class="authorized-by">
            <span data-bind="if: userHasAuth() && loaded()">
                    authorized
                    <span data-bind="if: dropboxName()">by {{ dropboxName }}</span>
                    <a data-bind="click: deleteKey" class="text-danger pull-right addon-auth">Disconnect Account</a>
            </span>

            <!-- Create Access Token Button -->
            <span data-bind="if: !userHasAuth() && loaded()">
                <a data-bind="attr: {href: urls().create}"
                   class="text-primary pull-right addon-auth">Connect Account</a>
            </span>
        </small>
    </h4>

    <!-- Flashed Messages -->
    <div class="help-block">
        <p data-bind="html: message, attr: {class: messageClass}"></p>
    </div>

<%include file="profile/addon_permissions.mako" />
</div>
