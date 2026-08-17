#!/usr/bin/perl
# index.cgi - Main page for Cloudflare DNS Auto Update Webmin Module

require './cf_dns-lib.pl';
&ui_print_header(undef, "Cloudflare DNS Auto Update", "", undef, 1, 1);

my $configs = &get_configs();
my $settings = &get_settings();
my $status = &get_service_status();
my $logs = &get_logs();

# Webmin standard table rendering
print &ui_form_start("action.cgi", "post");

# Section 1: Service Status Controls
print &ui_hidden("action", "toggle_service");
print &ui_table_start("Service Status & Control", "width=100%", 2);

my $status_html = $status 
    ? "<span style='color: #2e7d32; font-weight: bold; font-size: 15px;'>● Running</span>" 
    : "<span style='color: #c62828; font-weight: bold; font-size: 15px;'>● Stopped</span>";

my $toggle_btn = $status 
    ? "<a href='action.cgi?action=stop_service' class='ui_button' style='margin-left: 15px;'>Stop Service</a>" 
    : "<a href='action.cgi?action=start_service' class='ui_button' style='margin-left: 15px;'>Start Service</a>";

my $force_btn = "<a href='action.cgi?action=force_update' class='ui_button' style='margin-left: 10px;'>Force Update Now</a>";

print &ui_table_row("Status", $status_html . $toggle_btn . $force_btn);
print &ui_table_end();

print "<br />";

# Section 2: Domain Configurations Table
print &ui_table_start("Configured Domains & Records", "width=100%", 1);
print "<p style='margin: 5px 0 15px 0;'><a href='edit_config.cgi' class='ui_button' style='font-weight: bold;'>+ Add Domain Configuration</a></p>";

my @table_data;
if (@$configs) {
    foreach my $conf (@$configs) {
        my $rname = &html_escape($conf->{'RECORD_NAME'});
        my $zid = &html_escape($conf->{'ZONE_ID'});
        my $email = &html_escape($conf->{'AUTH_EMAIL'});
        my $proxied = $conf->{'PROXIED'} eq 'true' ? "Yes" : "No";
        
        my $actions = "<a href='edit_config.cgi?domain=$rname'>Edit</a> | " .
                      "<a href='action.cgi?action=delete_config&domain=$rname' onclick='return confirm(\"Delete configuration for $rname?\")'>Delete</a>";

        push(@table_data, [ "<b>$rname</b>", "<code>$zid</code>", $email, $proxied, $actions ]);
    }
    print &ui_columns_table([ "Record Name", "Zone ID", "Auth Email", "Proxied", "Actions" ], 100, \@table_data);
} else {
    print "<div style='padding: 15px; text-align: center;'><i>No domain configurations added yet. Click '+ Add Domain Configuration' above.</i></div>";
}
print &ui_table_end();

print "<br />";

# Section 3: Global Settings
print &ui_form_start("save_settings.cgi", "post");
print &ui_table_start("Global Settings", "width=100%", 2);
print &ui_table_row("Sync Interval (seconds)", 
    &ui_textbox("interval", $settings->{'interval'} || 30, 8) . 
    " &nbsp; " . 
    &ui_submit("Save Settings"));
print &ui_table_end();
print &ui_form_end();

print "<br />";

# Section 4: Service Logs
print &ui_table_start("Recent Service Logs", "width=100%", 1);
print "<p style='margin-bottom: 10px;'><a href='action.cgi?action=clear_logs' class='ui_button'>Clear Logs</a></p>";
print &ui_textarea("logs", $logs, 10, 100, "readonly", undef, "style='width:100%; font-family:monospace; background:#111; color:#0f0;'");
print &ui_table_end();

&ui_print_footer("/", $text{'index'});
