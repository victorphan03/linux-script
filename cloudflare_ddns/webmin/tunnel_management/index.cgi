#!/usr/bin/perl
# index.cgi - Main page for Cloudflare Tunnel Webmin Module

require './tunnel_management-lib.pl';
&ui_print_header(undef, "Cloudflare Tunnel Management", "", undef, 1, 1);

my $conf = &get_config();

# Section 1: Ingress Hostnames Table
print &ui_table_start("Tunnel Ingress Hostnames", "width=100%", 1);
print "<p style='margin: 5px 0 15px 0;'><a href='add_route.cgi' class='ui_button' style='font-weight: bold;'>+ Add New Hostname Route</a></p>";

my $routes_res = &run_python_cmd('get_routes', {});

if ($routes_res->{'status'} && ref($routes_res->{'msg'}) eq 'ARRAY' && @{$routes_res->{'msg'}}) {
    my @table_data;
    foreach my $item (@{$routes_res->{'msg'}}) {
        my $hname = &html_escape($item->{'hostname'});
        my $path = &html_escape($item->{'path'} || '*');
        my $svc = &html_escape($item->{'service'});

        my $actions = "<a href='action.cgi?action=delete_route&hostname=$hname&path=" . &html_escape($item->{'path'}||'') . "' onclick='return confirm(\"Delete hostname $hname?\")'>Delete</a>";

        push(@table_data, [ "<b>$hname</b>", $path, "<code>$svc</code>", $actions ]);
    }
    print &ui_columns_table([ "Hostname", "Path", "Service Target", "Actions" ], 100, \@table_data);
} else {
    my $err_msg = (ref($routes_res->{'msg'}) eq 'ARRAY') ? 'No ingress routes configured yet.' : ($routes_res->{'msg'} || 'API Credentials not fully configured.');
    print "<div style='padding: 15px; text-align: center; color: #c62828;'><i>$err_msg</i></div>";
}
print &ui_table_end();

print "<br />";

# Section 2: API & Tunnel Configuration Form
print &ui_form_start("save_config.cgi", "post");
print &ui_table_start("API & Tunnel Configuration", "width=100%", 2);

my $fetch_btn = "<button type='button' class='ui_button' onclick='fetchCloudflareOptions()' style='margin-left: 10px;'>Fetch Cloudflare Options</button>";
print &ui_table_row("Cloudflare API Token",
    "<input type='password' class='ui_textbox' name='api_token' id='api_token' size='50' value='" . &html_escape($conf->{'api_token'}) . "' placeholder='Bearer API Token' />" . $fetch_btn);

# Accounts Select Dropdown
print &ui_table_row("Account ID",
    "<select name='account_id' id='account_id' class='ui_select' style='min-width: 400px;' onchange='onAccountChange()'>" .
    ($conf->{'account_id'} ? "<option value='" . &html_escape($conf->{'account_id'}) . "'>" . &html_escape($conf->{'account_id'}) . "</option>" : "<option value=''>-- Enter API Token & click Fetch Options --</option>") .
    "</select>");

# Tunnels Select Dropdown
print &ui_table_row("Tunnel ID",
    "<select name='tunnel_id' id='tunnel_id' class='ui_select' style='min-width: 400px;'>" .
    ($conf->{'tunnel_id'} ? "<option value='" . &html_escape($conf->{'tunnel_id'}) . "'>" . &html_escape($conf->{'tunnel_id'}) . "</option>" : "<option value=''>-- Select Tunnel --</option>") .
    "</select>");

# Zones Select Dropdown
print &ui_table_row("Zone ID (Optional)",
    "<select name='zone_id' id='zone_id' class='ui_select' style='min-width: 400px;'>" .
    "<option value=''>-- Select Zone / Domain (Optional) --</option>" .
    ($conf->{'zone_id'} ? "<option value='" . &html_escape($conf->{'zone_id'}) . "' selected>" . &html_escape($conf->{'zone_id'}) . "</option>" : "") .
    "</select>");

print &ui_table_end();

print &ui_form_end([ 
    [ "save", "Save Configuration" ] 
]);

print "<script type='text/javascript'>
function fetchCloudflareOptions() {
    var tokenEl = document.getElementById('api_token');
    var accSelect = document.getElementById('account_id');
    var tunSelect = document.getElementById('tunnel_id');
    var zoneSelect = document.getElementById('zone_id');

    if (!tokenEl || !tokenEl.value.trim()) {
        alert('Please enter an API Token first');
        return;
    }
    var token = tokenEl.value.trim();

    if (accSelect) accSelect.innerHTML = '<option value=\"\">Fetching accounts...</option>';
    if (tunSelect) tunSelect.innerHTML = '<option value=\"\">Fetching tunnels...</option>';
    if (zoneSelect) zoneSelect.innerHTML = '<option value=\"\">Fetching zones...</option>';

    fetch('api.cgi?action=fetch_accounts&api_token=' + encodeURIComponent(token))
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (accSelect) accSelect.innerHTML = '<option value=\"\">-- Select Account --</option>';
            if (data.status && data.msg && data.msg.length > 0) {
                data.msg.forEach(function(acc) {
                    var opt = document.createElement('option');
                    opt.value = acc.id;
                    opt.textContent = acc.name + ' (' + acc.id + ')';
                    accSelect.appendChild(opt);
                });
                var chosenAcc = accSelect.value || data.msg[0].id;
                accSelect.value = chosenAcc;
                loadTunnels(token, chosenAcc);
            } else {
                if (accSelect) accSelect.innerHTML = '<option value=\"\">No Accounts found</option>';
                var err = (data && data.msg) ? data.msg : 'No Accounts found or API error';
                alert('Account API Error: ' + err);
            }
        })
        .catch(function(e) {
            if (accSelect) accSelect.innerHTML = '<option value=\"\">Error loading accounts</option>';
            alert('Error fetching accounts: ' + e);
        });

    fetch('api.cgi?action=fetch_zones&api_token=' + encodeURIComponent(token))
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (zoneSelect) zoneSelect.innerHTML = '<option value=\"\">-- Select Zone / Domain (Optional) --</option>';
            if (data.status && data.msg && data.msg.length > 0) {
                data.msg.forEach(function(zone) {
                    var opt = document.createElement('option');
                    opt.value = zone.id;
                    opt.textContent = zone.name + ' (' + zone.id + ')';
                    zoneSelect.appendChild(opt);
                });
            }
        });
}

function onAccountChange() {
    var tokenEl = document.getElementById('api_token');
    var accSelect = document.getElementById('account_id');
    if (tokenEl && accSelect && tokenEl.value.trim() && accSelect.value) {
        loadTunnels(tokenEl.value.trim(), accSelect.value);
    }
}

function loadTunnels(token, accId) {
    var tunSelect = document.getElementById('tunnel_id');
    if (tunSelect) tunSelect.innerHTML = '<option value=\"\">Fetching tunnels...</option>';

    fetch('api.cgi?action=fetch_tunnels&api_token=' + encodeURIComponent(token) + '&account_id=' + encodeURIComponent(accId))
        .then(function(response) { return response.json(); })
        .then(function(data) {
            if (tunSelect) tunSelect.innerHTML = '<option value=\"\">-- Select Tunnel --</option>';
            if (data.status && data.msg && data.msg.length > 0) {
                data.msg.forEach(function(tun) {
                    var opt = document.createElement('option');
                    opt.value = tun.id;
                    var st = tun.status ? ' [' + tun.status + ']' : '';
                    opt.textContent = tun.name + st + ' (' + tun.id + ')';
                    tunSelect.appendChild(opt);
                });
            } else {
                if (tunSelect) tunSelect.innerHTML = '<option value=\"\">No Tunnels found</option>';
                var err = (data && data.msg) ? data.msg : 'No Tunnels found';
                alert('Tunnel API Error: ' + err);
            }
        })
        .catch(function(e) {
            if (tunSelect) tunSelect.innerHTML = '<option value=\"\">Error loading tunnels</option>';
            alert('Error fetching tunnels: ' + e);
        });
}
</script>";

&ui_print_footer("/", $text{'index'});
