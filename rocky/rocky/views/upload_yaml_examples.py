# These objects are for displaying YAML examples on OOI Upload with YAML page. Field values created to deserialize from YAML file.

import yaml

network_1 = {
    'ooi_type': 'Network',
    'clearence': 2,
    'name': 'localhost'
}

ip_address_1 = {
    'ooi_type': 'IPAddress',
    'clearance': 2,
    'address': '2001:db8:3333:4444:5555:6666:7777:8888',
    'network': network_1
}
ip_address_2 = {
    'ooi_type': 'IPAddress',
    'clearance': 2,
    'address': '127.0.0.1',
    'network': network_1
}

ip_address_v4_1 = {
    'ooi_type': 'IPAddressV4',
    'clearance': 2,
    'address': '127.0.0.1',
    'network': network_1
}

ip_address_v6_1 = {
    'ooi_type': 'IPAddressV6',
    'clearance': 2,
    'address': 'fe80::c9e8:da3f:6fc7:8a32',
    'network': network_1
}

ip_port_1 = {
    'ooi_type': 'IPPort',
    'clearance': 2,
    'protocol': 'tcp',
    'port': 80,
    'address': ip_address_1,
    'state': 'filtered'
}

ip_v4_net_block_1 = {
    'ooi_type': 'IPV4NetBlock',
    'clearance': 2,
    'start_ip': ip_address_v4_1,
    'mask': 16,
    'network': network_1,
    'name': 'name_of_IPV4NetBlock__optional'
}

hostname_1 = {
    'ooi_type': 'Hostname',
    'clearance': 2,
    'name': 'localhost',
    'network': network_1
}

service_1 = {
    'ooi_type': 'Service',
    'clearance': 2,
    'name': 'name_of_Service'
}

ip_service_1 = {
    'ooi_type': 'IPService',
    'clearance': 2,
    'ip_port': ip_port_1,
    'service': service_1,
}

website_1 = {
    'ooi_type': 'Website',
    'clearance': 2,
    'ip_service': ip_service_1,
    'hostname': hostname_1,
}

hostname_http_url_1 = {
    'ooi_type': 'HostnameHTTPURL',
    'clearance': 2,
    'network': network_1,
    'scheme': 'http',
    'port': 80,
    'path': '/path_to_somewhere',
    'netloc': hostname_1,
}

ip_address_http_url_1 = {
    'ooi_type': 'IPAddressHTTPURL',
    'clearance': 2,
    'network': network_1,
    'scheme': 'http',
    'port': 80,
    'path': "/path_to_somewhere",
    'netloc': ip_address_v4_1,
}

http_resource_1 = {
    'ooi_type': 'HTTPResource',
    'clearance': 2,
    'website': website_1,
    'web_url': hostname_http_url_1,
}
http_header_1 = {
    'ooi_type': 'HTTPHeader',
    'clearance': 2,
    'resource': http_resource_1,
    'key': 'HTTPHeaderKey',
    'value': 'HTTPHeaderValue',
}

url_1 = {
    'ooi_type': 'URL',
    'clearance': 2,
    'network': network_1,
    'raw': "https://example.com",
}

restapi_1 = {
    'ooi_type': 'RESTAPI',
    'clearance': 2,
    'api_url': ip_address_http_url_1,
}

api_design_rule_1 = {
    'ooi_type': 'APIDesignRule',
    'clearance': 2,
    'name': 'APIDesignRuleName',
}

software_1 = {
    'ooi_type': 'Software',
    'clearance': 2,
    'name': 'name_of_Software',
    'version': 'version_of_Software__optional_field',
}

application_1 = {
    'ooi_type': 'Application',
    'clearance': 2,
    'name': 'name_of_Application',
}


cwe_finding_type_1 = {
    'ooi_type': 'CWEFindingType',
    'clearance': 2,
    'id': 'id_of_CWEFindingType',
}
finding_1 = {
    'ooi_type': 'Finding',
    'finding_type': cwe_finding_type_1,
    'ooi': network_1,
    'description': 'description_at_Finding__optional',
}

dns_txt_record_1 = {
    'ooi_type': 'DNSTXTRecord',
    'clearance': 2,
    'hostname': hostname_1,
    'dns_record_type': "TXT",
    'value': 'value_at_DNSTXTRecord',
}

dns_spf_record_1 = {
    'ooi_type': 'DNSSPFRecord',
    'clearance': 2,
    'value': 'value_at_DNSSPFRecord',
    'dns_txt_record': dns_txt_record_1,
}
dkim_selector_1 = {
    'ooi_type': 'DKIMSelector',
    'clearance': 2,
    'selector': 'selector_at_DKIMSelector',
    'hostname': hostname_1,
}

x509_certificate_1 = {
    'ooi_type': 'X509Certificate',
    'clearance': 2,
    'issuer': 'issuer_at_X509Certificate__optional',
    'valid_from': 'valid_from_at_X509Certificate',
    'valid_until': 'valid_until_at_X509Certificate',
    'serial_number': 'serial_number_at_X509Certificate',
}

subject_alternative_name_1 = {
    'ooi_type': 'SubjectAlternativeName',
    'certificate': x509_certificate_1,
    'hostname': hostname_1,
}

subject_alternative_name_2 = {
    'ooi_type': 'SubjectAlternativeName',
    'certificate': x509_certificate_1,
    'address': ip_address_v6_1,
}
subject_alternative_name_3 = {
    'ooi_type': 'SubjectAlternativeName',
    'certificate': x509_certificate_1,
    'name': 'subject_alternative_name_name_field',
}

web_url_1 = {
    'ooi_type': 'WebURL',
    'clearance': 2,
    'network': network_1,
    'scheme': 'http',
    'port': 80,
    'path': "/path_at_WebURL",
    'netloc': ip_address_v4_1,
}
web_url_2 = {
    'ooi_type': 'WebURL',
    'clearance': 2,
    'network': network_1,
    'scheme': 'http',
    'port': 80,
    'path': "/path_at_WebURL",
    'netloc': ip_address_v6_1,
}
web_url_3 = {
    'ooi_type': 'WebURL',
    'clearance': 2,
    'network': network_1,
    'scheme': 'http',
    'port': 80,
    'path': "/path_at_WebURL",
    'netloc': hostname_1,
}
# DNSRecord base type automatically switch to proper class according to dns_record_type field.
dns_record_1 = {
    'ooi_type': 'DNSRecord',
    'clearance': 2,
    'hostname': hostname_1,
    'dns_record_type': "A (Subclasses depends on this field, possible values: A, AAAA, CAA, CNAME, MX, NS, PTR, SOA, TXT)",
    'value': 'strval',
    'address': ip_address_v4_1,
}

autonomous_system_1 = {
    'ooi_type': 'AutonomousSystem',
    'clearance': 2,
    'number': "1234",
    'name': 'name_of_AutonomousSystem',
}

ip_v6_net_block_1 = {
    'ooi_type': 'IPV6NetBlock',
    'clearance': 2,
    'start_ip': ip_address_v6_1,
    'mask': 16,
    'network': network_1,
    'name': 'name_of_IPV6NetBlock__optional',
}
# NetBlock b}ase type automatically switch to IPV4NetBlock or IPV6NetBlock according to start_ip field.
net_block_1 = {
    'ooi_type': 'NetBlock',
    'clearance': 2,
    'network': network_1,
    'start_ip': ip_address_v4_1,
    'mask': 16,
}
net_block_2 = {
    'ooi_type': 'NetBlock',
    'clearance': 2,
    'network': network_1,
    'start_ip': ip_address_v6_1,
    'mask': 16,
}

dns_zone_1 = {
    'ooi_type': 'DNSZone',
    'clearance': 2,
    'hostname': hostname_1,
}

resolved_hostname_1 = {
    'ooi_type': 'ResolvedHostname',
    'clearance': 2,
    'hostname': hostname_1,
    'address': ip_address_v4_1,
}

tls_cipher_1 = {
    'ooi_type': 'TLSCipher',
    'clearance': 2,
    'ip_service': ip_service_1,
    'suites': { 'key': "this_is_a_random_dict_value_for_TLSCipher" },
}

http_header_url_1 = {
    'ooi_type': 'HTTPHeaderURL',
    'clearance': 2,
    'header': http_header_1,
    'url': url_1,
}
http_header_hostname_1 = {
    'ooi_type': 'HTTPHeaderHostname',
    'clearance': 2,
    'header': http_header_1,
    'hostname': hostname_1,
}
image_metadata_1 = {
    'ooi_type': 'ImageMetadata',
    'clearance': 2,
    'resource': http_resource_1,
    'url': url_1,
    'image_info': {},
}

api_design_rule_result_1 = {
    'ooi_type': 'APIDesignRuleResult',
    'clearance': 2,
    'rest_api': restapi_1,
    'rule': api_design_rule_1,
    'passed': True,
    'message': 'message_at_APIDesignRuleResult',
}
security_txt_1 = {
    'ooi_type': 'SecurityTXT',
    'clearance': 2,
    'website': website_1,
    'url': url_1,
}

software_instance_1 = {
    'ooi_type': 'SoftwareInstance',
    'clearance': 2,
    'ooi': network_1,
    'software': software_1,
}

external_scan_1 = {
    'ooi_type': 'ExternalScan',
    'clearance': 2,
    'name': 'name_of_ExternalScan',
}

question_1 = {
  'ooi_type': 'Question',
    'clearance': 2,
    'ooi': network_1,
    'schema_id': 'schema_id_at_Question',
    'json_schema': '{ "title":"Arguments"}',
}

incident_1 = {
    'ooi_type': 'Incident',
    'clearance': 2,
    'application': application_1,
    'event_id': 'event_id_at_Incident',
    'event_type': 'event_type_at_Incident',
    'event_title': 'event_title_at_Incident',
    'severity': 'severity_at_Incident',
    'meta_data': { 'arbitrary_field': "[]" },
}

geographic_point_1 = {
    'ooi_type': 'GeographicPoint',
    'clearance': 2,
    'ooi': network_1,
    'longitude': 10,
    'latitude': 10,
}

# FindingType base type should have an id field that contains "<SubclassName> ..."
finding_type_1 = {
    'ooi_type': 'FindingType',
    'clearance': 2,
    'id': '<SUBCLASS>-id_of_FindingType',
    'description': 'description_at_FindingType',
}
finding_type_2 = {
    'ooi_type': 'FindingType',
    'clearance': 2,
    'id': 'ADRFindingType-id_of_FindingType',
    'description': 'description_at_FindingType',
}
finding_type_3 = {
    'ooi_type': 'FindingType',
    'clearance': 2,
    'id': 'CVEFindingType-id_of_FindingType',
    'description': 'description_at_FindingType',
}
finding_type_4 = {
    'ooi_type': 'FindingType',
    'clearance': 2,
    'id': 'CWEFindingType-id_of_FindingType',
    'description': 'description_at_FindingType',
}
finding_type_5 = {
    'ooi_type': 'FindingType',
    'clearance': 2,
    'id': 'CAPECFindingType-id_of_FindingType',
    'description': 'description_at_FindingType',
}
finding_type_6 = {
    'ooi_type': 'FindingType',
    'clearance': 2,
    'id': 'RetireJSFindingType-id_of_FindingType',
    'description': 'description_at_FindingType',
}
finding_type_7 = {
    'ooi_type': 'FindingType',
    'clearance': 2,
    'id': 'SnykFindingType-id_of_FindingType',
    'description': 'description_at_FindingType',
}
finding_type_8 = {
    'ooi_type': 'FindingType',
    'clearance': 2,
    'id': 'KATFindingType-id_of_FindingType',
    'description': 'description_at_FindingType',
}
adr_finding_type_1 = {
    'ooi_type': 'ADRFindingType',
    'clearance': 2,
    'id': 'id_of_ADRFindingType',
}
cve_finding_type_1 = {
    'ooi_type': 'CVEFindingType',
    'clearance': 2,
    'id': 'id_of_CVEFindingType',
}
capec_finding_type_1 = {
    'ooi_type': 'CAPECFindingType',
    'clearance': 2,
    'id': 'id_of_CAPECFindingType',
}
retire_js_finding_type_1 = {
    'ooi_type': 'RetireJSFindingType',
    'clearance': 2,
    'id': 'id_of_RetireJSFindingType',
}
snyk_finding_type_1 = {
    'ooi_type': 'SnykFindingType',
    'clearance': 2,
    'id': 'id_of_SnykFindingType',
}
kat_finding_type_1 = {
    'ooi_type': 'KATFindingType',
    'clearance': 2,
    'id': 'id_of_KATFindingType',
}
muted_finding_1 = {
    'ooi_type': 'MutedFinding',
    'clearance': 2,
    'finding': finding_1,
    'reason': 'reason_at_MutedFinding__optional',
}

dns_a_record_1 = {
    'ooi_type': 'DNSARecord',
    'clearance': 2,
    'hostname': hostname_1,
    'dns_record_type': "A",
    'value': 'value_at_DNSARecord',
    'address': ip_address_v4_1,
}
dns_aaaa_record_1 = {
    'ooi_type': 'DNSAAAARecord',
    'clearance': 2,
    'hostname': hostname_1,
    'dns_record_type': "AAAA",
    'value': 'value_at_DNSAAAARecord',
    'address': ip_address_v6_1,
}
dns_mx_record_1 = {
    'ooi_type': 'DNSMXRecord',
    'clearance': 2,
    'hostname': hostname_1,
    'dns_record_type': "MX",
    'value': 'value_at_DNSMXRecord',
}
dns_ns_record_1 = {
    'ooi_type': 'DNSNSRecord',
    'clearance': 2,
    'hostname': hostname_1,
    'dns_record_type': "NS",
    'value': 'value_at_DNSNSRecord',
    'name_server_hostname': hostname_1,
}
dns_cname_record_1 = {
    'ooi_type': 'DNSCNAMERecord',
    'clearance': 2,
    'hostname': hostname_1,
    'dns_record_type': "CNAME",
    'value': 'value_at_DNSCNAMERecord',
    'target_hostname': hostname_1,
}
dns_soa_record_1 = {
    'ooi_type': 'DNSSOARecord',
    'clearance': 2,
    'hostname': hostname_1,
    'dns_record_type': "SOA",
    'value': 'value_at_DNSSOARecord',
    'soa_hostname': hostname_1,
}
dns_ptr_record_1 = {
    'ooi_type': 'DNSPTRRecord',
    'clearance': 2,
    'hostname': hostname_1,
    'dns_record_type': "PTR",
    'value': 'value_at_DNSPTRRecord',
    'address': ip_address_v4_1,
}

dns_caa_record_1 = {
    'ooi_type': 'DNSCAARecord',
    'clearance': 2,
    'hostname': hostname_1,
    'dns_record_type': "CAA",
    'value': 'value_at_DNSCAARecord',
    'tag': "iodef",
}
nx_domain_1 = {
    'ooi_type': 'NXDOMAIN',
    'clearance': 2,
    'hostname': hostname_1,
}

dns_spf_mechanism_ip_1 = {
    'ooi_type': 'DNSSPFMechanismIP',
    'clearance': 2,
    'qualifier': "+",
    'ip': ip_address_v4_1,
    'spf_record': dns_spf_record_1,
    'mechanism': 'mechanism_at_DNSSPFMechanism',
}
dns_spf_mechanism_hostname_1 = {
    'ooi_type': 'DNSSPFMechanismHostname',
    'clearance': 2,
    'spf_record': dns_spf_record_1,
    'mechanism': 'mechanism_at_DNSSPFMechanism',
    'hostname': hostname_1,
    'qualifier': "+",
}
dns_spf_mechanism_net_block_1 = {
    'ooi_type': 'DNSSPFMechanismNetBlock',
    'clearance': 2,
    'spf_record': dns_spf_record_1,
    'mechanism': 'mechanism_at_DNSSPFMechanism',
    'netblock': ip_v4_net_block_1,
    'qualifier': "+",
}
dmarc_txt_record_1 = {
    'ooi_type': 'DMARCTXTRecord',
    'clearance': 2,
    'value': 'value_at_DMARCTXTRecord',
    'hostname': hostname_1,
}
dkim_exists_1 = {
    'ooi_type': 'DKIMExists',
    'clearance': 2,
    'hostname': hostname_1,
}
dkim_key_1 = {
    'ooi_type': 'DKIMKey',
    'clearance': 2,
    'key': 'key_at_DKIMKey',
    'dkim_selector': dkim_selector_1,
}

config_1 = {
    'ooi_type': 'Config',
    'clearance': 2,
    'ooi': network_1,
    'bit_id': 'bit_id_at_Config',
    'config': {},
}

subject_alternative_name_hostname_1 = {
    'ooi_type': 'SubjectAlternativeNameHostname',
    'clearance': 2,
    'certificate': x509_certificate_1,
    'hostname': hostname_1,
}
subject_alternative_name_ip_1 = {
    'ooi_type': 'SubjectAlternativeNameIP',
    'clearance': 2,
    'certificate': x509_certificate_1,
    'address': ip_address_v6_1,
}
subject_alternative_name_qualifier_1 = {
    'ooi_type': 'SubjectAlternativeNameQualifier',
    'clearance': 2,
    'certificate': x509_certificate_1,
    'name': 'name_of_SubjectAlternativeNameQualifier',
}



all_examples = {
    'Network': [network_1],
    'IPAddress': [ip_address_1, ip_address_2],
    'IPAddressV4': [ip_address_v4_1],
    'IPAddressV6': [ip_address_v6_1],
    'IPPort': [ip_port_1],
    'IPV4NetBlock': [ip_v4_net_block_1],
    'Hostname': [hostname_1],
    'Service': [service_1],
    'IPService': [ip_service_1],
    'Website': [website_1],
    'HostnameHTTPURL': [hostname_http_url_1],
    'IPAddressHTTPURL': [ip_address_http_url_1],
    'HTTPResource': [http_resource_1],
    'HTTPHeader': [http_header_1],
    'URL': [url_1],
    'RESTAPI': [restapi_1],
    'APIDesignRule': [api_design_rule_1],
    'Software': [software_1],
    'Application': [application_1],
    'CWEFindingType': [cwe_finding_type_1],
    'Finding': [finding_1],
    'DNSTXTRecord': [dns_txt_record_1],
    'DNSSPFRecord': [dns_spf_record_1],
    'DKIMSelector': [dkim_selector_1],
    'X509Certificate': [x509_certificate_1],
    'SubjectAlternativeName': [subject_alternative_name_1, subject_alternative_name_2, subject_alternative_name_3],
    'WebURL': [web_url_1, web_url_2, web_url_3],
    'DNSRecord': [dns_record_1],
    'AutonomousSystem': [autonomous_system_1],
    'IPV6NetBlock': [ip_v6_net_block_1],
    'NetBlock': [net_block_1, net_block_2],
    'DNSZone': [dns_zone_1],
    'ResolvedHostname': [resolved_hostname_1],
    'TLSCipher': [tls_cipher_1],
    'HTTPHeaderURL': [http_header_url_1],
    'HTTPHeaderHostname': [http_header_hostname_1],
    'ImageMetadata': [image_metadata_1],
    'APIDesignRuleResult': [api_design_rule_result_1],
    'SecurityTXT': [security_txt_1],
    'SoftwareInstance': [software_instance_1],
    'ExternalScan': [external_scan_1],
    'Question': [question_1],
    'Incident': [incident_1],
    'GeographicPoint': [geographic_point_1],
    'FindingType': [
        finding_type_1,
        finding_type_2,
        finding_type_3,
        finding_type_4,
        finding_type_5,
        finding_type_6,
        finding_type_7,
        finding_type_8
    ],
    'ADRFindingType': [adr_finding_type_1],
    'CVEFindingType': [cve_finding_type_1],
    'CAPECFindingType': [capec_finding_type_1],
    'RetireJSFindingType': [retire_js_finding_type_1],
    'SnykFindingType': [snyk_finding_type_1],
    'KATFindingType': [kat_finding_type_1],
    'MutedFinding': [muted_finding_1],
    'DNSARecord': [dns_a_record_1],
    'DNSAAAARecord': [dns_aaaa_record_1],
    'DNSMXRecord': [dns_mx_record_1],
    'DNSNSRecord': [dns_ns_record_1],
    'DNSCNAMERecord': [dns_cname_record_1],
    'DNSSOARecord': [dns_soa_record_1],
    'DNSPTRRecord': [dns_ptr_record_1],
    'DNSCAARecord': [dns_caa_record_1],
    'NXDOMAIN': [nx_domain_1],
    'DNSSPFMechanismIP': [dns_spf_mechanism_ip_1],
    'DNSSPFMechanismHostname': [dns_spf_mechanism_hostname_1],
    'DNSSPFMechanismNetBlock': [dns_spf_mechanism_net_block_1],
    'DMARCTXTRecord': [dmarc_txt_record_1],
    'DKIMExists': [dkim_exists_1],
    'DKIMKey': [dkim_key_1],
    'Config': [config_1],
    'SubjectAlternativeNameHostname': [subject_alternative_name_hostname_1],
    'SubjectAlternativeNameIP': [subject_alternative_name_ip_1],
    'SubjectAlternativeNameQualifier': [subject_alternative_name_qualifier_1],
}

# # # Serialize to YAML # # #

class NoAlias(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True

ooi_yaml_examples = {}

for k, v in all_examples.items():
    ooi_yaml_examples[k] = list(yaml.dump(ooi, Dumper=NoAlias, indent=4, sort_keys=False) for ooi in v)

