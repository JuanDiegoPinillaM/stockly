"""Horario de atención por día y su resumen agrupado para mostrar.

El horario se guarda por día (`schedule` en Warehouse). Para la página de
tiendas lo agrupamos: días consecutivos con el mismo horario se muestran como un
rango (p. ej. "Lunes a viernes 7:00 a.m. – 9:00 p.m.") y los festivos se anexan
si coinciden ("Fines de semana y festivos …").
"""

DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
DAY_NAMES = {
    'mon': 'Lunes', 'tue': 'Martes', 'wed': 'Miércoles', 'thu': 'Jueves',
    'fri': 'Viernes', 'sat': 'Sábado', 'sun': 'Domingo',
}


def _fmt_time(value):
    """'07:00' → '7:00 a.m.'."""
    try:
        h, m = value.split(':')
        h, m = int(h), int(m)
    except (AttributeError, ValueError):
        return value
    suffix = 'a.m.' if h < 12 else 'p.m.'
    return f'{(h % 12) or 12}:{m:02d} {suffix}'


def _day_hours(entry):
    """De la entrada de un día devuelve (clave_de_grupo, texto) o None si no está
    definida. La clave permite agrupar días con el mismo horario."""
    if not isinstance(entry, dict):
        return None
    if entry.get('closed'):
        return ('closed',), 'Cerrado'
    open_, close = entry.get('open'), entry.get('close')
    if not open_ or not close:
        return None
    return ('open', open_, close), f'{_fmt_time(open_)} – {_fmt_time(close)}'


def _label_days(keys):
    if keys == ['sat', 'sun']:
        return 'Fines de semana'
    if keys == ['mon', 'tue', 'wed', 'thu', 'fri']:
        return 'Lunes a viernes'
    names = [DAY_NAMES[k] for k in keys]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f'{names[0]} y {names[1]}'
    return f'{names[0]} a {names[-1]}'


def summarize_schedule(schedule):
    """Devuelve [{'days': 'Lunes a viernes', 'hours': '7:00 a.m. – 9:00 p.m.'}, …].

    Agrupa días consecutivos con el mismo horario; los festivos se anexan a un
    grupo si coinciden, o van como línea aparte ("Festivos").
    """
    if not isinstance(schedule, dict) or not schedule:
        return []

    groups = []
    for dk in DAY_KEYS:
        res = _day_hours(schedule.get(dk))
        if res is None:
            continue
        group_key, text = res
        prev = groups[-1] if groups else None
        consecutive = prev and DAY_KEYS.index(prev['keys'][-1]) == DAY_KEYS.index(dk) - 1
        if prev and prev['key'] == group_key and consecutive:
            prev['keys'].append(dk)
        else:
            groups.append({'keys': [dk], 'key': group_key, 'text': text})

    out = [{'days': _label_days(g['keys']), 'hours': g['text']} for g in groups]

    holiday = _day_hours(schedule.get('holidays'))
    if holiday is not None:
        _, text = holiday
        for row in out:
            if row['hours'] == text:
                row['days'] += ' y festivos'
                break
        else:
            out.append({'days': 'Festivos', 'hours': text})
    return out
