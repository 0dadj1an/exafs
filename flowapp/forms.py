from flask_wtf import FlaskForm
from wtforms import StringField, SelectMultipleField, TextAreaField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, Email, NumberRange, Optional

from validators import IPAddress, NetRangeString, PortString, address_with_mask, address_in_range, \
    whole_world_range

TCP_FLAGS = [('SYN', 'SYN'), ('ACK', 'ACK'), ('FIN', 'FIN'), ('URG', 'URG'), ('PSH', 'PSH'), ('RST', 'RST'),
             ('ECE', 'ECE'), ('CWR', 'CWR'), ('NS', 'NS')]


class UserForm(FlaskForm):
    """
    User Form object
    used in Admin
    """
    uuid = StringField(
        'Unique User ID', validators=[DataRequired("Please provide UUID"),
                                      Email("Please provide valid email")]
    )

    email = StringField(
        'Email', validators=[Optional(),
                             Email("Please provide valid email")]
    )

    comment = StringField(
        'Notice', validators=[Optional()]
    )

    name = StringField(
        'Name', validators=[Optional()]
    )

    phone = StringField(
        'Contact phone', validators=[Optional()]
    )

    role_ids = SelectMultipleField(u'Role',
                                   coerce=int,
                                   validators=[DataRequired("Select at last one role")])

    org_ids = SelectMultipleField(u'Organization',
                                  coerce=int,
                                  validators=[DataRequired("Select at last one Organization")])


class OrganizationForm(FlaskForm):
    """
    Organization form object
    used in Admin
    """
    name = StringField(
        'Organization name',
        validators=[Optional(), Length(max=150)]
    )

    arange = TextAreaField('Organization Adress Range - one range per row',
                           validators=[Optional(), NetRangeString()]
                           )


class ActionForm(FlaskForm):
    """
    Action form object
    used in Admin
    """
    name = StringField(
        'Action short name',
        validators=[Length(max=150)]
    )

    command = StringField(
        'ExaBGP command',
        validators=[Length(max=150)]
    )

    description = StringField('Action description')


class RTBHForm(FlaskForm):
    """
    RoadToBlackHole rule form
    """
    ipv4 = StringField('Source IPv4 address',
                       validators=[Optional(), IPAddress(message='provide valid IPv4 adress')]
                       )

    ipv4_mask = IntegerField('Source IPv4  mask (bytes)',
                             validators=[Optional(), NumberRange(min=0, max=255, message='invalid mask value (0-255)')])

    ipv6 = StringField('Source IPv6 address',
                       validators=[Optional(), IPAddress(message='provide valid IPv6 adress')]
                       )
    ipv6_mask = IntegerField('Source mask (bytes)',
                             validators=[Optional(), NumberRange(min=0, max=255, message='invalid mask value (0-255)')])

    community = SelectField('Community',
                            choices=[('2852:666', '2852:666'), ('40965:666', '40965:666'), ('xxxxx:666', 'xxxxx:666')],
                            validators=[DataRequired()])

    expires = StringField(
        'Expires'
    )

    comment = arange = TextAreaField('Comments'
                                     )


class IPForm(FlaskForm):
    """
    Base class for IPv4 and IPv6 rules
    """
    def __init__(self, *args, **kwargs):
        super(IPForm, self).__init__(*args, **kwargs)
        self.net_ranges = None

    zero_address = None
    source = None
    source_mask = None
    dest = None
    dest_mask = None
    flags = SelectMultipleField('TCP flag(s)',
                                choices=TCP_FLAGS,
                                validators=[Optional()])

    source_port = StringField(
        'Source port(s) -  ; separated ',
        validators=[Optional(), Length(max=255), PortString()]
    )

    dest_port = StringField(
        'Destination port(s) - ; separated',
        validators=[Optional(), Length(max=255), PortString()]
    )

    packet_len = StringField('Packet length', validators=[Optional(), Length(max=255)])

    action = SelectField(u'Action',
                         coerce=int,
                         validators=[DataRequired()])

    expires = StringField('Expires')

    comment = arange = TextAreaField('Comments')

    def validate(self):
        """
        custom validation method
        :return: boolean
        """
        result = True

        if not FlaskForm.validate(self):
            result = False

        result = result and self.validate_source_address()
        result = result and self.validate_dest_address()
        result = result and self.validate_address_ranges()
        result = result and self.validate_ipv_specific()

        return result

    def validate_source_address(self):
        """
        validate source address, set error message if validation fails
        :return: boolean validation result
        """
        if self.source.data and not address_with_mask(self.source.data, self.source_mask.data):
            self.source.errors.append(
                "This is not valid combination of address {} and mask {}.".format(self.source.data,
                                                                                  self.source_mask.data))
            return False

        return True

    def validate_dest_address(self):
        """
        validate dest address, set error message if validation fails
        :return: boolean validation result
        """
        if self.dest.data and not address_with_mask(self.dest.data, self.dest_mask.data):
            self.dest.errors.append(
                "This is not valid combination of address {} and mask {}.".format(self.dest.data,
                                                                                  self.dest_mask.data))
            return False

        return True

    def validate_address_ranges(self):
        """
        validates if the address of source is in the user range
        if the source and dest address are empty, check if the user is member of whole world organization
        :return: boolean validation result
        """
        if not (self.source.data or self.dest.data):
            whole_world_member = whole_world_range(self.net_ranges, self.zero_address)
            print(whole_world_member)
            if not whole_world_member:
                self.source.errors.append("Source or dest must be in organization range : {}.".format(self.net_ranges))
                self.dest.errors.append("Source or dest must be in organization range : {}.".format(self.net_ranges))
                return False
        else:
            source_in_range = address_in_range(self.source.data, self.net_ranges)
            dest_in_range = address_in_range(self.dest.data, self.net_ranges)

            if not (source_in_range or dest_in_range):
                self.source.errors.append("Source or dest must be in organization range : {}.".format(self.net_ranges))
                self.dest.errors.append("Source or dest must be in organization range : {}.".format(self.net_ranges))
                return False

        return True

    def validate_ipv_specific(self):
        """
        abstract method must be implemented in the subclass
        """
        pass


class IPv4Form(IPForm):
    """
    IPv4 form object
    """
    def __init__(self, *args, **kwargs):
        super(IPv4Form, self).__init__(*args, **kwargs)
        self.net_ranges = None

    zero_address = u"0.0.0.0"
    source = StringField('Source address',
                         validators=[Optional(), IPAddress(message='provide valid IPv4 adress')]
                         )

    source_mask = IntegerField('Source mask (bytes)',
                               validators=[Optional(), NumberRange(min=0, max=32, message='invalid mask value (0-32)')])

    dest = StringField('Destination address',
                       validators=[Optional(), IPAddress(message='provide valid IPv4 adress')]
                       )

    dest_mask = IntegerField('Destination mask (bytes)',
                             validators=[Optional(), NumberRange(min=0, max=32, message='invalid mask value (0-32)')])

    protocol = SelectField('Protocol',
                           choices=[('tcp', 'TCP'), ('udp', 'UDP'), ('icmp', 'ICMP')],
                           validators=[DataRequired()])

    def validate_ipv_specific(self):
        """
        validate protocol and flags, set error message if validation fails
        :return: boolean validation result
        """

        if len(self.flags.data) > 0 and self.protocol.data != 'tcp':
            self.flags.errors.append("Can not set TCP flags for protocol {} !".format(self.protocol.data.upper()))
            return False
        return True


class IPv6Form(IPForm):
    """
    IPv6 form object
    """
    def __init__(self, *args, **kwargs):
        super(IPv6Form, self).__init__(*args, **kwargs)
        self.net_ranges = None

    zero_address = u"::"
    source = StringField('Source address',
                         validators=[Optional(), IPAddress(message='provide valid IPv6 adress')]
                         )

    source_mask = IntegerField('Source prefix length (bytes)',
                               validators=[Optional(),
                                           NumberRange(min=0, max=128, message='invalid prefix value (0-128)')])

    dest = StringField('Destination address',
                       validators=[Optional(), IPAddress(message='provide valid IPv6 adress')]
                       )

    dest_mask = IntegerField('Destination prefix length (bytes)',
                             validators=[Optional(),
                                         NumberRange(min=0, max=128, message='invalid prefix value (0-128)')])

    next_header = SelectField('Next Header',
                              choices=[('tcp', 'TCP'), ('udp', 'UDP'), ('icmp', 'ICMP')],
                              validators=[DataRequired()])

    def validate_ipv_specific(self):
        """
        validate next header and flags, set error message if validation fails
        :return: boolean validation result
        """
        if len(self.flags.data) > 0 and self.next_header.data != 'tcp':
            self.flags.errors.append("Can not set TCP flags for next-header {} !".format(self.protocol.data.upper()))
            return False

        return True
