from datetime import date


def get_days_from_day0(DAY_0, target_date):

    target_date_parts = target_date.split('/')
    target_date = date(int(target_date_parts[2]), int(target_date_parts[0]), int(target_date_parts[1]))

    day0_parts = DAY_0.split('/')
    day0_date = date(int(day0_parts[2]), int(day0_parts[0]), int(day0_parts[1]))

    delta = target_date - day0_date

    return delta.days


def get_days_to_t0(t0, DAY_0):

    t0_parts = t0.split('-')
    t0_date = date(int(t0_parts[0]), int(t0_parts[1]), int(t0_parts[2]))

    day0_parts = DAY_0.split('/')
    day0_date = date(int(day0_parts[2]), int(day0_parts[0]), int(day0_parts[1]))

    delta = t0_date - day0_date

    return delta.days

