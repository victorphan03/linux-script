#!/usr/bin/perl
# edit_config.cgi - Form for adding/editing Cloudflare domain DDNS config

require './cf_dns-lib.pl';
&ReadParse();

my $domain = $in{'domain'};
my $configs = &get_configs();
my $target_conf = {};

if ($domain) {
    foreach my $c (@$configs) {
        if ($c->{'RECORD_NAME'} eq $domain) {
            $target_conf = $c;
            last;
        }
    }
}

my $title = $domain ? "Edit Domain Configuration: $domain" : "Add New Domain Configuration";
&ui_print_header(undef, $title, "", undef, 0, 0);

print &ui_form_start("save_config.cgi", "post");
print &ui_hidden("old_domain", $domain);

print &ui_table_start($title, "width=100%", 2);

print &ui_table_row("Cloudflare Email (AUTH_EMAIL)",
    &ui_textbox("AUTH_EMAIL", $target_conf->{'AUTH_EMAIL'}, 50));

print &ui_table_row("Global API Key / Token (AUTH_KEY)",
    &ui_textbox("AUTH_KEY", $target_conf->{'AUTH_KEY'}, 50, 0, 0, "type='password'"));

print &ui_table_row("Zone ID (ZONE_ID)",
    &ui_textbox("ZONE_ID", $target_conf->{'ZONE_ID'}, 50));

print &ui_table_row("Record Name / Subdomain",
    &ui_textbox("RECORD_NAME", $target_conf->{'RECORD_NAME'}, 50, 0, 0, "placeholder='e.g. sub.domain.com'"));

my $proxied_checked = $target_conf->{'PROXIED'} eq 'true' ? 1 : 0;
print &ui_table_row("Proxy Status (PROXIED)",
    &ui_checkbox("PROXIED", "true", "Enable Cloudflare Proxy", $proxied_checked));

print &ui_table_end();

print &ui_form_end([ [ undef, "Save Configuration" ] ]);

&ui_print_footer("index.cgi", "Return to Module Main");
