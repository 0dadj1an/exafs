# flowapp/views/admin.py
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, flash, request, url_for, session
import requests

from ..forms import RTBHForm, IPv4Form, IPv6Form, NetInRange
from ..models import Action, RTBH, Flowspec4, Flowspec6, Log, get_user_nets
from ..auth import auth_required, admin_required, user_or_admin_required, localhost_only
from ..utils import webpicker_to_datetime, flash_errors, datetime_to_webpicker

from flowapp import db, messages

rules = Blueprint('rules', __name__, template_folder='templates')

DATA_MODELS = {1: RTBH, 4: Flowspec4, 6: Flowspec6}
DATA_FORMS = {1: RTBHForm, 4: IPv4Form, 6: IPv6Form}
DATA_TEMPLATES = {1: 'forms/rtbh_rule.j2', 4: 'forms/ipv4_rule.j2', 6: 'forms/ipv6_rule.j2'}
DATA_TABLES = {1: 'RTBH', 4: 'flow string - type of rule to be deletedspec4', 6: 'flowspec6'}
ROUTE_MODELS = {1: messages.create_rtbh, 4: messages.create_ipv4, 6: messages.create_ipv6}


@rules.route('/reactivate/<int:rule_type>/<int:rule_id>', methods=['GET', 'POST'])
@auth_required
@user_or_admin_required
def reactivate_rule(rule_type, rule_id):
    """
    Set new time for the rule of given type identified by id
    :param rule_type: string - type of rule
    :param rule_id: integer - id of the rule
    """
    model_name = DATA_MODELS[rule_type]
    form_name = DATA_FORMS[rule_type]

    model = db.session.query(model_name).get(rule_id)
    form = form_name(request.form, obj=model)
    form.net_ranges = get_user_nets(session['user_id'])

    if rule_type > 2:
        form.action.choices = [(g.id, g.name)
                               for g in db.session.query(Action).order_by('name')]
        form.action.data = model.action_id

    if rule_type == 4:
        form.protocol.data = model.protocol

    if rule_type == 6:
        form.next_header.data = model.next_header

    # do not need to validate - all is readonly
    if request.method == 'POST':
        model.expires = webpicker_to_datetime(form.expires.data)
        db.session.commit()
        flash(u'Rule reactivated', 'alert-success')
        # announce routes
        announce_routes()
        return redirect(url_for('index'))
    else:
        flash_errors(form)

    form.expires.data = datetime_to_webpicker(model.expires)
    for field in form:
        if field.name not in ['expires', 'csrf_token']:
            field.render_kw = {'disabled': 'disabled'}

    action_url = url_for('rules.reactivate_rule', rule_type=rule_type, rule_id=rule_id)

    return render_template(DATA_TEMPLATES[rule_type], form=form, action_url=action_url)


@rules.route('/delete/<int:rule_type>/<int:rule_id>', methods=['GET'])
@auth_required
@user_or_admin_required
def delete_rule(rule_type, rule_id):
    """
    Delete rule with given id and type
    :param rule_type: string - type of rule to be deleted
    :param rule_id: integer - rule id
    """
    model_name = DATA_MODELS[rule_type]
    route_model = ROUTE_MODELS[rule_type]

    model = db.session.query(model_name).get(rule_id)

    # withdraw route
    route = route_model(model, messages.WITHDRAW)
    withdraw_route(route)

    # delete from db
    db.session.delete(model)
    db.session.commit()
    flash(u'Rule deleted', 'alert-success')

    return redirect(url_for('index'))


@rules.route('/add_ipv4_rule', methods=['GET', 'POST'])
@auth_required
@user_or_admin_required
def ipv4_rule():
    net_ranges = get_user_nets(session['user_id'])
    form = IPv4Form(request.form)

    # add values to form instance
    form.action.choices = [(g.id, g.name)
                           for g in db.session.query(Action).order_by('name')]

    form.net_ranges = net_ranges

    if request.method == 'POST' and form.validate():

        model = Flowspec4(
            source=form.source.data,
            source_mask=form.source_mask.data,
            source_port=form.source_port.data,
            destination=form.dest.data,
            destination_mask=form.dest_mask.data,
            destination_port=form.dest_port.data,
            protocol=form.protocol.data,
            flags=";".join(form.flags.data),
            packet_len=form.packet_len.data,
            expires=webpicker_to_datetime(form.expires.data),
            comment=form.comment.data,
            action_id=form.action.data,
            user_id=session['user_id']
        )
        db.session.add(model)
        db.session.commit()
        flash(u'IPv4 Rule saved', 'alert-success')

        # announce routes
        announce_routes()
        return redirect(url_for('index'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                print(u"Error in the %s field - %s" % (
                    getattr(form, field).label.text,
                    error
                ))

    default_expires = datetime.now() + timedelta(days=7)
    form.expires.data = datetime_to_webpicker(default_expires)

    return render_template('forms/ipv4_rule.j2', form=form, action_url=url_for('rules.ipv4_rule'))


@rules.route('/add_ipv6_rule', methods=['GET', 'POST'])
@auth_required
@user_or_admin_required
def ipv6_rule():
    net_ranges = get_user_nets(session['user_id'])
    form = IPv6Form(request.form)
    form.action.choices = [(g.id, g.name)
                           for g in db.session.query(Action).order_by('name')]

    form.net_ranges = net_ranges

    if request.method == 'POST' and form.validate():

        model = Flowspec6(
            source=form.source.data,
            source_mask=form.source_mask.data,
            source_port=form.source_port.data,
            destination=form.dest.data,
            destination_mask=form.dest_mask.data,
            destination_port=form.dest_port.data,
            next_header=form.next_header.data,
            flags=";".join(form.flags.data),
            packet_len=form.packet_len.data,
            expires=webpicker_to_datetime(form.expires.data),
            comment=form.comment.data,
            action_id=form.action.data,
            user_id=session['user_id']
        )
        db.session.add(model)
        db.session.commit()
        flash(u'IPv6 Rule saved', 'alert-success')

        # announce routes
        announce_routes()
        return redirect(url_for('index'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                print(u"Error in the %s field - %s" % (
                    getattr(form, field).label.text,
                    error
                ))

    default_expires = datetime.now() + timedelta(days=7)
    form.expires.data = datetime_to_webpicker(default_expires)

    return render_template('forms/ipv6_rule.j2', form=form, action_url=url_for('rules.ipv6_rule'))


@rules.route('/add_rtbh_rule', methods=['GET', 'POST'])
@auth_required
@user_or_admin_required
def rtbh_rule():
    net_ranges = get_user_nets(session['user_id'])
    form = RTBHForm(request.form)

    # add validator to instance but only once
    if len(form.ipv4.validators) == 2:
        form.ipv4.validators.append(NetInRange(net_ranges))

    if len(form.ipv6.validators) == 2:
        form.ipv6.validators.append(NetInRange(net_ranges))

    if request.method == 'POST' and form.validate():

        model = RTBH(
            ipv4=form.ipv4.data,
            ipv4_mask=form.ipv4_mask.data,
            ipv6=form.ipv6.data,
            ipv6_mask=form.ipv6_mask.data,
            community=form.community.data,
            expires=webpicker_to_datetime(form.expires.data),
            comment=form.comment.data,
            user_id=session['user_id']
        )
        db.session.add(model)
        db.session.commit()
        flash(u'RTBH Rule saved', 'alert-success')

        # announce routes
        announce_routes()
        return redirect(url_for('index'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                print(u"Error in the %s field - %s" % (
                    getattr(form, field).label.text,
                    error
                ))

    default_expires = datetime.now() + timedelta(days=7)
    form.expires.data = datetime_to_webpicker(default_expires)

    return render_template('forms/rtbh_rule.j2', form=form, action_url=url_for('rules.rtbh_rule'))


@rules.route('/export')
@auth_required
@admin_required
def export():
    rules4 = db.session.query(Flowspec4).order_by(Flowspec4.expires.desc()).all()
    rules6 = db.session.query(Flowspec6).order_by(Flowspec6.expires.desc()).all()
    rules = {4: rules4, 6: rules6}

    actions = db.session.query(Action).all()
    actions = {action.id: action for action in actions}

    rules_rtbh = db.session.query(RTBH).order_by(RTBH.expires.desc()).all()

    announce_routes()

    return render_template('pages/home.j2', rules=rules, actions=actions, rules_rtbh=rules_rtbh, today=datetime.now())


@rules.route('/announce_all', methods=['GET'])
@localhost_only
def announce_all():
    print(request.remote_addr)
    announce_routes()
    return ' '


def announce_routes():
    """
    get actual valid routes from db and send it to ExaBGB api
    curl --form "command=announce route 100.10.0.0/24 next-hop self" http://localhost:5000/
    @TODO take the request away, use some kind of messaging (maybe celery?)
    """
    today = datetime.now()
    rules4 = db.session.query(Flowspec4).filter(Flowspec4.expires >= today).order_by(
        Flowspec4.expires.desc()).all()
    rules6 = db.session.query(Flowspec6).filter(Flowspec6.expires >= today).order_by(
        Flowspec6.expires.desc()).all()
    rules_rtbh = db.session.query(RTBH).order_by(RTBH.expires.desc()).all()

    output4 = [messages.create_ipv4(rule) for rule in rules4]
    output6 = [messages.create_ipv6(rule) for rule in rules6]
    output_rtbh = [messages.create_rtbh(rule) for rule in rules_rtbh]

    output = []
    output.extend(output4)
    output.extend(output6)
    output.extend(output_rtbh)

    for message in output:
        requests.post('http://localhost:5000/', data={'command': message})


def withdraw_route(route):
    """
    withdraw deleted route
    @TODO take the request away, use some kind of messaging (maybe celery?)
    """
    requests.post('http://localhost:5000/', data={'command': route})

def log_route(route_model, route_type):
    """
    Convert route to EXAFS message and log it to database
    :param route_model: model with route object
    :param route_type: string
    :return: None
    """
