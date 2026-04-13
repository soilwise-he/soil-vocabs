vcl 4.0;

backend default {
    .host = "fuseki";
    .port = "3030";
}

sub vcl_backend_response {
    set beresp.ttl = 1w;
    set beresp.do_gzip = true;
}
