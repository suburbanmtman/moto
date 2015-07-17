from __future__ import unicode_literals
from boto.ec2.elb.attributes import (
    ConnectionSettingAttribute,
    ConnectionDrainingAttribute,
    AccessLogAttribute,
    CrossZoneLoadBalancingAttribute,
)
from boto.ec2.elb.policies import (
    Policies,
    AppCookieStickinessPolicy,
    LBCookieStickinessPolicy,
    OtherPolicy,
)

from moto.core.responses import BaseResponse
from .models import elb_backends


class ELBResponse(BaseResponse):

    @property
    def elb_backend(self):
        return elb_backends[self.region]

    def create_load_balancer(self):
        """
        u'Scheme': [u'internet-facing'],
        """
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        availability_zones = [value[0] for key, value in self.querystring.items() if "AvailabilityZones.member" in key]
        ports = []
        port_index = 1
        while True:
            try:
                protocol = self.querystring['Listeners.member.{0}.Protocol'.format(port_index)][0]
            except KeyError:
                break
            lb_port = self.querystring['Listeners.member.{0}.LoadBalancerPort'.format(port_index)][0]
            instance_port = self.querystring['Listeners.member.{0}.InstancePort'.format(port_index)][0]
            ssl_certificate_id = self.querystring.get('Listeners.member.{0}.SSLCertificateId'.format(port_index), [None])[0]
            ports.append([protocol, lb_port, instance_port, ssl_certificate_id])
            port_index += 1

        self.elb_backend.create_load_balancer(
            name=load_balancer_name,
            zones=availability_zones,
            ports=ports,
        )
        template = self.response_template(CREATE_LOAD_BALANCER_TEMPLATE)
        return template.render()

    def create_load_balancer_listeners(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        ports = []
        port_index = 1
        while True:
            try:
                protocol = self.querystring['Listeners.member.{0}.Protocol'.format(port_index)][0]
            except KeyError:
                break
            lb_port = self.querystring['Listeners.member.{0}.LoadBalancerPort'.format(port_index)][0]
            instance_port = self.querystring['Listeners.member.{0}.InstancePort'.format(port_index)][0]
            ssl_certificate_id = self.querystring.get('Listeners.member.{0}.SSLCertificateId'.format(port_index)[0], None)
            ports.append([protocol, lb_port, instance_port, ssl_certificate_id])
            port_index += 1

        self.elb_backend.create_load_balancer_listeners(name=load_balancer_name, ports=ports)

        template = self.response_template(CREATE_LOAD_BALANCER_LISTENERS_TEMPLATE)
        return template.render()

    def describe_load_balancers(self):
        names = [value[0] for key, value in self.querystring.items() if "LoadBalancerNames.member" in key]
        load_balancers = self.elb_backend.describe_load_balancers(names)
        template = self.response_template(DESCRIBE_LOAD_BALANCERS_TEMPLATE)
        return template.render(load_balancers=load_balancers)

    def delete_load_balancer_listeners(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        ports = []
        port_index = 1
        while True:
            try:
                port = self.querystring['LoadBalancerPorts.member.{0}'.format(port_index)][0]
            except KeyError:
                break

            port_index += 1
            ports.append(int(port))

        self.elb_backend.delete_load_balancer_listeners(load_balancer_name, ports)
        template = self.response_template(DELETE_LOAD_BALANCER_LISTENERS)
        return template.render()

    def delete_load_balancer(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        self.elb_backend.delete_load_balancer(load_balancer_name)
        template = self.response_template(DELETE_LOAD_BALANCER_TEMPLATE)
        return template.render()

    def configure_health_check(self):
        check = self.elb_backend.configure_health_check(
            load_balancer_name=self.querystring.get('LoadBalancerName')[0],
            timeout=self.querystring.get('HealthCheck.Timeout')[0],
            healthy_threshold=self.querystring.get('HealthCheck.HealthyThreshold')[0],
            unhealthy_threshold=self.querystring.get('HealthCheck.UnhealthyThreshold')[0],
            interval=self.querystring.get('HealthCheck.Interval')[0],
            target=self.querystring.get('HealthCheck.Target')[0],
        )
        template = self.response_template(CONFIGURE_HEALTH_CHECK_TEMPLATE)
        return template.render(check=check)

    def register_instances_with_load_balancer(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        instance_ids = [value[0] for key, value in self.querystring.items() if "Instances.member" in key]
        template = self.response_template(REGISTER_INSTANCES_TEMPLATE)
        load_balancer = self.elb_backend.register_instances(load_balancer_name, instance_ids)
        return template.render(load_balancer=load_balancer)

    def set_load_balancer_listener_sslcertificate(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        ssl_certificate_id = self.querystring['SSLCertificateId'][0]
        lb_port = self.querystring['LoadBalancerPort'][0]

        self.elb_backend.set_load_balancer_listener_sslcertificate(load_balancer_name, lb_port, ssl_certificate_id)

        template = self.response_template(SET_LOAD_BALANCER_SSL_CERTIFICATE)
        return template.render()

    def deregister_instances_from_load_balancer(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        instance_ids = [value[0] for key, value in self.querystring.items() if "Instances.member" in key]
        template = self.response_template(DEREGISTER_INSTANCES_TEMPLATE)
        load_balancer = self.elb_backend.deregister_instances(load_balancer_name, instance_ids)
        return template.render(load_balancer=load_balancer)

    def describe_load_balancer_attributes(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        load_balancer = self.elb_backend.describe_load_balancers(load_balancer_name)[0]
        template = self.response_template(DESCRIBE_ATTRIBUTES_TEMPLATE)
        return template.render(attributes=load_balancer.attributes)

    def modify_load_balancer_attributes(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        load_balancer = self.elb_backend.describe_load_balancers(load_balancer_name)[0]

        def parse_attribute(attribute_name):
            """
            Transform self.querystring parameters matching `LoadBalancerAttributes.attribute_name.attribute_key`
            into a dictionary of (attribute_name, attribute_key)` pairs.
            """
            attribute_prefix = "LoadBalancerAttributes." + attribute_name
            return dict((key.lstrip(attribute_prefix), value[0]) for key, value in self.querystring.items() if key.startswith(attribute_prefix))

        cross_zone = parse_attribute("CrossZoneLoadBalancing")
        if cross_zone:
            attribute = CrossZoneLoadBalancingAttribute()
            attribute.enabled = cross_zone["Enabled"] == "true"
            self.elb_backend.set_cross_zone_load_balancing_attribute(load_balancer_name, attribute)

        access_log = parse_attribute("AccessLog")
        if access_log:
            attribute = AccessLogAttribute()
            attribute.enabled = access_log["Enabled"] == "true"
            attribute.s3_bucket_name = access_log["S3BucketName"]
            attribute.s3_bucket_prefix = access_log["S3BucketPrefix"]
            attribute.emit_interval = access_log["EmitInterval"]
            self.elb_backend.set_access_log_attribute(load_balancer_name, attribute)

        connection_draining = parse_attribute("ConnectionDraining")
        if connection_draining:
            attribute = ConnectionDrainingAttribute()
            attribute.enabled = connection_draining["Enabled"] == "true"
            attribute.timeout = connection_draining["Timeout"]
            self.elb_backend.set_connection_draining_attribute(load_balancer_name, attribute)

        connection_settings = parse_attribute("ConnectionSettings")
        if connection_settings:
            attribute = ConnectionSettingAttribute()
            attribute.idle_timeout = connection_settings["IdleTimeout"]
            self.elb_backend.set_connection_settings_attribute(load_balancer_name, attribute)

        template = self.response_template(MODIFY_ATTRIBUTES_TEMPLATE)
        return template.render(attributes=load_balancer.attributes)

    def create_load_balancer_policy(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        load_balancer = self.elb_backend.describe_load_balancers(load_balancer_name)[0]

        other_policy = OtherPolicy()
        policy_name = [value[0] for key, value in self.querystring.items() if "PolicyName" in key][0]
        other_policy.policy_name = policy_name

        self.elb_backend.create_lb_other_policy(load_balancer_name, other_policy)

        template = self.response_template(CREATE_LOAD_BALANCER_POLICY_TEMPLATE)
        return template.render()

    def create_app_cookie_stickiness_policy(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        load_balancer = self.elb_backend.describe_load_balancers(load_balancer_name)[0]

        policy = AppCookieStickinessPolicy()
        policy_name = [value[0] for key, value in self.querystring.items() if "PolicyName" in key][0]
        policy.policy_name = policy_name
        cookie_name = [value[0] for key, value in self.querystring.items() if "CookieName" in key][0]
        policy.cookie_name = cookie_name

        self.elb_backend.create_app_cookie_stickiness_policy(load_balancer_name, policy)

        template = self.response_template(CREATE_LOAD_BALANCER_POLICY_TEMPLATE)
        return template.render()

    def create_lbcookie_stickiness_policy(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        load_balancer = self.elb_backend.describe_load_balancers(load_balancer_name)[0]

        policy = AppCookieStickinessPolicy()
        policy_name = [value[0] for key, value in self.querystring.items() if "PolicyName" in key][0]
        policy.policy_name = policy_name
        cookie_expirations = [value[0] for key, value in self.querystring.items() if "CookieExpirationPeriod" in key]
        if cookie_expirations:
            policy.cookie_expiration_period = int(cookie_expirations[0])
        else:
            policy.cookie_expiration_period = None

        self.elb_backend.create_lb_cookie_stickiness_policy(load_balancer_name, policy)

        template = self.response_template(CREATE_LOAD_BALANCER_POLICY_TEMPLATE)
        return template.render()

    def set_load_balancer_policies_of_listener(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        load_balancer = self.elb_backend.describe_load_balancers(load_balancer_name)[0]
        load_balancer_port = int(self.querystring.get('LoadBalancerPort')[0])

        mb_listener = [l for l in load_balancer.listeners if int(l.load_balancer_port) == load_balancer_port]
        if mb_listener:
            policies = []
            policy_index = 1
            while True:
                try:
                    policy = self.querystring['PolicyNames.member.{0}'.format(policy_index)][0]
                except KeyError:
                    break

                policy_index += 1
                policies.append(str(policy))

            self.elb_backend.set_load_balancer_policies_of_listener(load_balancer_name, load_balancer_port, policies)
        # else: explode?

        template = self.response_template(SET_LOAD_BALANCER_POLICIES_OF_LISTENER_TEMPLATE)
        return template.render()
    
    def set_load_balancer_policies_for_backend_server(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        load_balancer = self.elb_backend.describe_load_balancers(load_balancer_name)[0]
        instance_port = int(self.querystring.get('InstancePort')[0])

        mb_backend = [b for b in load_balancer.backends if int(b.instance_port) == instance_port]
        if mb_backend:
            policies = []
            policy_index = 1
            while True:
                try:
                    policy = self.querystring['PolicyNames.member.{0}'.format(policy_index)][0]
                except KeyError:
                    break

                policy_index += 1
                policies.append(str(policy))

            self.elb_backend.set_load_balancer_policies_of_backend_server(load_balancer_name, instance_port, policies)
        
        # else: explode?

        template = self.response_template(SET_LOAD_BALANCER_POLICIES_FOR_BACKEND_SERVER_TEMPLATE)
        return template.render()

    def describe_instance_health(self):
        load_balancer_name = self.querystring.get('LoadBalancerName')[0]
        instance_ids = [value[0] for key, value in self.querystring.items() if "Instances.member" in key]
        if len(instance_ids) == 0:
            instance_ids = self.elb_backend.describe_load_balancers(load_balancer_name)[0].instance_ids
        template = self.response_template(DESCRIBE_INSTANCE_HEALTH_TEMPLATE)
        return template.render(instance_ids=instance_ids)


CREATE_LOAD_BALANCER_TEMPLATE = """<CreateLoadBalancerResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
    <DNSName>tests.us-east-1.elb.amazonaws.com</DNSName>
</CreateLoadBalancerResult>"""

CREATE_LOAD_BALANCER_LISTENERS_TEMPLATE = """<CreateLoadBalancerListenersResponse xmlns="http://elasticloadbalancing.amazon aws.com/doc/2012-06-01/">
  <CreateLoadBalancerListenersResult/>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
</CreateLoadBalancerListenersResponse>"""

DELETE_LOAD_BALANCER_TEMPLATE = """<DeleteLoadBalancerResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
</DeleteLoadBalancerResult>"""

DESCRIBE_LOAD_BALANCERS_TEMPLATE = """<DescribeLoadBalancersResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DescribeLoadBalancersResult>
    <LoadBalancerDescriptions>
      {% for load_balancer in load_balancers %}
        <member>
          <SecurityGroups>
          </SecurityGroups>
          <LoadBalancerName>{{ load_balancer.name }}</LoadBalancerName>
          <CreatedTime>2013-01-01T00:00:00.19000Z</CreatedTime>
          <HealthCheck>
            {% if load_balancer.health_check %}
              <Interval>{{ load_balancer.health_check.interval }}</Interval>
              <Target>{{ load_balancer.health_check.target }}</Target>
              <HealthyThreshold>{{ load_balancer.health_check.healthy_threshold }}</HealthyThreshold>
              <Timeout>{{ load_balancer.health_check.timeout }}</Timeout>
              <UnhealthyThreshold>{{ load_balancer.health_check.unhealthy_threshold }}</UnhealthyThreshold>
            {% endif %}
          </HealthCheck>
          <VPCId>vpc-56e10e3d</VPCId>
          <ListenerDescriptions>
            {% for listener in load_balancer.listeners %}
              <member>
                <PolicyNames>
                  {% for policy_name in listener.policy_names %}
                    <member>{{ policy_name }}</member>
                  {% endfor %}
                </PolicyNames>
                <Listener>
                  <Protocol>{{ listener.protocol }}</Protocol>
                  <LoadBalancerPort>{{ listener.load_balancer_port }}</LoadBalancerPort>
                  <InstanceProtocol>{{ listener.protocol }}</InstanceProtocol>
                  <InstancePort>{{ listener.instance_port }}</InstancePort>
                  <SSLCertificateId>{{ listener.ssl_certificate_id }}</SSLCertificateId>
                </Listener>
              </member>
            {% endfor %}
          </ListenerDescriptions>
          <Instances>
            {% for instance_id in load_balancer.instance_ids %}
              <member>
                <InstanceId>{{ instance_id }}</InstanceId>
              </member>
            {% endfor %}
          </Instances>
          <Policies>
            <AppCookieStickinessPolicies>
            {% if load_balancer.policies.app_cookie_stickiness_policies %}
                {% for policy in load_balancer.policies.app_cookie_stickiness_policies %}
                    <member>
                        <CookieName>{{ policy.cookie_name }}</CookieName>
                        <PolicyName>{{ policy.policy_name }}</PolicyName>
                    </member>
                {% endfor %}
            {% endif %}
            </AppCookieStickinessPolicies>
            <LBCookieStickinessPolicies>
            {% if load_balancer.policies.lb_cookie_stickiness_policies %}
                {% for policy in load_balancer.policies.lb_cookie_stickiness_policies %}
                    <member>
                        {% if policy.cookie_expiration_period %}
                        <CookieExpirationPeriod>{{ policy.cookie_expiration_period }}</CookieExpirationPeriod>
                        {% endif %}
                        <PolicyName>{{ policy.policy_name }}</PolicyName>
                    </member>
                {% endfor %}
            {% endif %}
            </LBCookieStickinessPolicies>
            <OtherPolicies>
            {% if load_balancer.policies.other_policies %}
                {% for policy in load_balancer.policies.other_policies %}
                    <member>{{ policy.policy_name }}</member>
                {% endfor %}
            {% endif %}
            </OtherPolicies>
          </Policies>
          <AvailabilityZones>
            {% for zone in load_balancer.zones %}
              <member>{{ zone }}</member>
            {% endfor %}
          </AvailabilityZones>
          <CanonicalHostedZoneName>tests.us-east-1.elb.amazonaws.com</CanonicalHostedZoneName>
          <CanonicalHostedZoneNameID>Z3ZONEID</CanonicalHostedZoneNameID>
          <Scheme>internet-facing</Scheme>
          <DNSName>tests.us-east-1.elb.amazonaws.com</DNSName>
          <BackendServerDescriptions>
          {% for backend in load_balancer.backends %}
            <member>
                {% if backend.instance_port %}
                <InstancePort>{{ backend.instance_port }}</InstancePort>
                {% endif %}
                {% if backend.policy_names %}
                    <PolicyNames>
                        {% for policy in backend.policy_names %}
                            <member>{{ policy }}</member>
                        {% endfor %}
                    </PolicyNames>
                    {% endif %}
            </member>
          {% endfor %}
          </BackendServerDescriptions>
          <Subnets>
          </Subnets>
        </member>
      {% endfor %}
    </LoadBalancerDescriptions>
  </DescribeLoadBalancersResult>
  <ResponseMetadata>
    <RequestId>f9880f01-7852-629d-a6c3-3ae2-666a409287e6dc0c</RequestId>
  </ResponseMetadata>
</DescribeLoadBalancersResponse>"""

CONFIGURE_HEALTH_CHECK_TEMPLATE = """<ConfigureHealthCheckResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <HealthCheck>
    <Interval>{{ check.interval }}</Interval>
    <Target>{{ check.target }}</Target>
    <HealthyThreshold>{{ check.healthy_threshold }}</HealthyThreshold>
    <Timeout>{{ check.timeout }}</Timeout>
    <UnhealthyThreshold>{{ check.unhealthy_threshold }}</UnhealthyThreshold>
  </HealthCheck>
</ConfigureHealthCheckResult>"""

REGISTER_INSTANCES_TEMPLATE = """<RegisterInstancesWithLoadBalancerResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <Instances>
    {% for instance_id in load_balancer.instance_ids %}
      <member>
        <InstanceId>{{ instance_id }}</InstanceId>
      </member>
    {% endfor %}
  </Instances>
</RegisterInstancesWithLoadBalancerResult>"""

DEREGISTER_INSTANCES_TEMPLATE = """<DeregisterInstancesWithLoadBalancerResult xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <Instances>
    {% for instance_id in load_balancer.instance_ids %}
      <member>
        <InstanceId>{{ instance_id }}</InstanceId>
      </member>
    {% endfor %}
  </Instances>
</DeregisterInstancesWithLoadBalancerResult>"""

SET_LOAD_BALANCER_SSL_CERTIFICATE = """<SetLoadBalancerListenerSSLCertificateResponse xmlns="http://elasticloadbalan cing.amazonaws.com/doc/2012-06-01/">
 <SetLoadBalancerListenerSSLCertificateResult/>
<ResponseMetadata>
    <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
</ResponseMetadata>
</SetLoadBalancerListenerSSLCertificateResponse>"""


DELETE_LOAD_BALANCER_LISTENERS = """<DeleteLoadBalancerListenersResponse xmlns="http://elasticloadbalan cing.amazonaws.com/doc/2012-06-01/">
 <DeleteLoadBalancerListenersResult/>
<ResponseMetadata>
    <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
</ResponseMetadata>
</DeleteLoadBalancerListenersResponse>"""

DESCRIBE_ATTRIBUTES_TEMPLATE = """<DescribeLoadBalancerAttributesResponse  xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DescribeLoadBalancerAttributesResult>
    <LoadBalancerAttributes>
      <AccessLog>
        <Enabled>{{ attributes.access_log.enabled }}</Enabled>
        {% if attributes.access_log.enabled %}
        <S3BucketName>{{ attributes.access_log.s3_bucket_name }}</S3BucketName>
        <S3BucketPrefix>{{ attributes.access_log.s3_bucket_prefix }}</S3BucketPrefix>
        <EmitInterval>{{ attributes.access_log.emit_interval }}</EmitInterval>
        {% endif %}
      </AccessLog>
      <ConnectionSettings>
        <IdleTimeout>{{ attributes.connecting_settings.idle_timeout }}</IdleTimeout>
      </ConnectionSettings>
      <CrossZoneLoadBalancing>
        <Enabled>{{ attributes.cross_zone_load_balancing.enabled }}</Enabled>
      </CrossZoneLoadBalancing>
      <ConnectionDraining>
        <Enabled>{{ attributes.connection_draining.enabled }}</Enabled>
        {% if attributes.connection_draining.enabled %}
        <Timeout>{{ attributes.connection_draining.timeout }}</Timeout>
        {% endif %}
      </ConnectionDraining>
    </LoadBalancerAttributes>
  </DescribeLoadBalancerAttributesResult>
  <ResponseMetadata>
    <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeLoadBalancerAttributesResponse>
"""

MODIFY_ATTRIBUTES_TEMPLATE = """<ModifyLoadBalancerAttributesResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <ModifyLoadBalancerAttributesResult>
  <LoadBalancerName>my-loadbalancer</LoadBalancerName>
    <LoadBalancerAttributes>
      <AccessLog>
        <Enabled>{{ attributes.access_log.enabled }}</Enabled>
        {% if attributes.access_log.enabled %}
        <S3BucketName>{{ attributes.access_log.s3_bucket_name }}</S3BucketName>
        <S3BucketPrefix>{{ attributes.access_log.s3_bucket_prefix }}</S3BucketPrefix>
        <EmitInterval>{{ attributes.access_log.emit_interval }}</EmitInterval>
        {% endif %}
      </AccessLog>
      <ConnectionSettings>
        <IdleTimeout>{{ attributes.connecting_settings.idle_timeout }}</IdleTimeout>
      </ConnectionSettings>
      <CrossZoneLoadBalancing>
        <Enabled>{{ attributes.cross_zone_load_balancing.enabled }}</Enabled>
      </CrossZoneLoadBalancing>
      <ConnectionDraining>
        <Enabled>{{ attributes.connection_draining.enabled }}</Enabled>
        {% if attributes.connection_draining.enabled %}
        <Timeout>{{ attributes.connection_draining.timeout }}</Timeout>
        {% endif %}
      </ConnectionDraining>
    </LoadBalancerAttributes>
  </ModifyLoadBalancerAttributesResult>
  <ResponseMetadata>
    <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
  </ResponseMetadata>
</ModifyLoadBalancerAttributesResponse>
"""

CREATE_LOAD_BALANCER_POLICY_TEMPLATE = """<CreateLoadBalancerPolicyResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <CreateLoadBalancerPolicyResult/>
  <ResponseMetadata>
      <RequestId>83c88b9d-12b7-11e3-8b82-87b12EXAMPLE</RequestId>
  </ResponseMetadata>
</CreateLoadBalancerPolicyResponse>
"""

SET_LOAD_BALANCER_POLICIES_OF_LISTENER_TEMPLATE = """<SetLoadBalancerPoliciesOfListenerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
    <SetLoadBalancerPoliciesOfListenerResult/>
    <ResponseMetadata>
        <RequestId>07b1ecbc-1100-11e3-acaf-dd7edEXAMPLE</RequestId>
    </ResponseMetadata>
</SetLoadBalancerPoliciesOfListenerResponse>
"""

SET_LOAD_BALANCER_POLICIES_FOR_BACKEND_SERVER_TEMPLATE = """<SetLoadBalancerPoliciesForBackendServerResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
    <SetLoadBalancerPoliciesForBackendServerResult/>
    <ResponseMetadata>
        <RequestId>0eb9b381-dde0-11e2-8d78-6ddbaEXAMPLE</RequestId>
    </ResponseMetadata>
</SetLoadBalancerPoliciesForBackendServerResponse>
"""

DESCRIBE_INSTANCE_HEALTH_TEMPLATE = """<DescribeInstanceHealthResponse xmlns="http://elasticloadbalancing.amazonaws.com/doc/2012-06-01/">
  <DescribeInstanceHealthResult>
    <InstanceStates>
      {% for instance_id in instance_ids %}
      <member>
        <Description>N/A</Description>
        <InstanceId>{{ instance_id }}</InstanceId>
        <State>InService</State>
        <ReasonCode>N/A</ReasonCode>
      </member>
      {% endfor %}
    </InstanceStates>
  </DescribeInstanceHealthResult>
  <ResponseMetadata>
    <RequestId>1549581b-12b7-11e3-895e-1334aEXAMPLE</RequestId>
  </ResponseMetadata>
</DescribeInstanceHealthResponse>"""
