#!/usr/bin/perl
# add_route.cgi - Form to add new hostname ingress route

require './tunnel_management-lib.pl';
&ui_print_header(undef, "Add Published Application Route", "", undef, 0, 0);

print &ui_form_start("save_route.cgi", "post");

print &ui_table_start("Route Details", "width=100%", 2);

print &ui_table_row("Subdomain (Optional)",
    &ui_textbox("subdomain", "", 40, 0, 0, "placeholder='e.g. www or app'"));

print &ui_table_row("Domain Name",
    &ui_textbox("domain", "", 40, 0, 0, "placeholder='e.g. example.com' required"));

print &ui_table_row("Path (Optional)",
    &ui_textbox("path", "", 40, 0, 0, "placeholder='e.g. /api'"));

my $service_types = [
    [ "http", "HTTP" ],
    [ "https", "HTTPS" ],
    [ "tcp", "TCP" ],
    [ "udp", "UDP" ],
    [ "ssh", "SSH" ],
    [ "rdp", "RDP" ],
    [ "unix", "UNIX Socket" ]
];

print &ui_table_row("Service Protocol",
    &ui_select("service_type", "http", $service_types));

print &ui_table_row("Target Address & Port",
    &ui_textbox("target_url", "", 40, 0, 0, "placeholder='e.g. localhost:8080 or 127.0.0.1:80' required"));

print &ui_table_end();

print &ui_form_end([ [ undef, "Add Hostname Route" ] ]);

&ui_print_footer("index.cgi", "Return to Tunnel Management Main");
