. as $root
| {
    metadata: {
      description: "Censys host data",
      created_at: (now | strftime("%Y-%m-%d")),
      data_sources: ["censys_hosts"],
      hosts_count: length,
      ips_analyzed: [.[].ip],
      rollups: {
        by_country: ( [ .[].location.country_code ] | map(select(. != null)) | group_by(.) | map({ (.[0]): length }) | add ),
        by_service: ( [ .[].services[]?.service_name, .[].services[]?.protocol ]
                      | map(select(. != null))
                      | group_by(.)
                      | map({ (.[0]): length })
                      | add )
      }
    },
    hosts: [
      .[] | {
        ip,
        location,
        autonomous_system,
        dns,
        operating_system,
        services: (
          [ .services[]? | {
              port,
              protocol: (.protocol // .service_name),
              banner,
              software,
              vulnerabilities,
              tls_enabled,
              certificate,
              authentication_required,
              error_message,
              response_details,
              malware_detected,
              access_restricted
            }
          ]
        ),
        threat_intelligence
      }
    ]
  }
