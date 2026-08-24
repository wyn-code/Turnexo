"""Email sending services for TurnoGo."""
import resend

from app.core.config import RESEND_API_KEY, FRONTEND_URL
from app.services.qr_service import generar_qr_png_bytes

resend.api_key = RESEND_API_KEY

FROM_ADDRESS = "TurnoGo <contacto@turnogo.app>"


def send_verification_email(
    email: str,
    token: str,
):
    """Send an email verification link to the user."""
    verification_link = (
        f"{FRONTEND_URL}/verify-email/{token}")

    params = {
        "from": FROM_ADDRESS,
        "to": [email],
        "subject": "Verificá tu cuenta",
        "html": f"""
            <h2>Bienvenido a Turnogo</h2>

            <p>
                Hacé click en el siguiente enlace
                para verificar tu cuenta:
            </p>

            <a href="{verification_link}">
                Verificar cuenta
            </a>

            <p>
                Este enlace expirará en 24 horas.
            </p>
        """,
    }

    response = resend.Emails.send(params)

    return response


def send_reset_password_email(
    email: str,
    token: str,
):
    """Send a password reset email to the user."""
    reset_link = f"{FRONTEND_URL}/restablecer-contrasena/{token}"

    params = {
        "from": FROM_ADDRESS,
        "to": [email],
        "subject": "Restablecer contraseña",
        "html": f"""
            <h2>Restablecer contraseña</h2>
            <p>
                Recibimos una solicitud para cambiar
                la contraseña de tu cuenta.
            </p>
            <p>
                Hacé click en el siguiente enlace:
            </p>
            <a href="{reset_link}">
                Restablecer contraseña
            </a>
            <p>
                Este enlace expirará en 24 horas.
            </p>
            <p>
                Si no solicitaste el cambio, ignorá
                este mensaje.
            </p>
        """,
    }

    try:
        response = resend.Emails.send(params)
        print("=== RESPUESTA RESEND ===")
        print(response)
        return response
    except Exception as e:
        print("=== ERROR ENVIANDO EMAIL RESET PASSWORD ===")
        print(f"Error: {e}")
        raise


def send_booking_confirmation_email(
    email: str,
    id_turno: int,
    nombre_negocio: str,
    nombre_servicio: str,
    nombre_empleado: str | None,
    fecha: str,
    hora: str,
    direccion: str | None,
    telefono_negocio: str | None,
):
    """Send a booking confirmation email with QR to the client."""
    if not email:
        return

    qr_bytes = generar_qr_png_bytes(id_turno)

    empleado_html = (
        f'<tr><td style="padding:6px 0;color:#555;">Profesional</td>'
        f'<td style="padding:6px 0;font-weight:600;">{nombre_empleado}</td></tr>'
        if nombre_empleado
        else ""
    )

    direccion_html = (
        f'<tr><td style="padding:6px 0;color:#555;">Dirección</td>'
        f'<td style="padding:6px 0;font-weight:600;">{direccion}</td></tr>'
        if direccion
        else ""
    )

    telefono_html = (
        f'<tr><td style="padding:6px 0;color:#555;">Teléfono</td>'
        f'<td style="padding:6px 0;font-weight:600;">{telefono_negocio}</td></tr>'
        if telefono_negocio
        else ""
    )

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;color:#222;">
        <h2 style="color:#b45309;">¡Tu turno en {nombre_negocio} está confirmado!</h2>

        <p>Te enviamos los datos de tu reserva junto con un código QR
           que deberás presentar al momento de tu turno.</p>

        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
            <tr>
                <td style="padding:6px 0;color:#555;">Servicio</td>
                <td style="padding:6px 0;font-weight:600;">{nombre_servicio}</td>
            </tr>
            {empleado_html}
            <tr>
                <td style="padding:6px 0;color:#555;">Fecha</td>
                <td style="padding:6px 0;font-weight:600;">{fecha}</td>
            </tr>
            <tr>
                <td style="padding:6px 0;color:#555;">Hora</td>
                <td style="padding:6px 0;font-weight:600;">{hora}</td>
            </tr>
            {direccion_html}
            {telefono_html}
        </table>

        <div style="text-align:center;margin:24px 0;">
            <img src="cid:qr_turno" alt="QR del turno" style="width:180px;height:180px;" />
            <p style="font-size:12px;color:#888;">Código QR de tu turno #{id_turno}</p>
        </div>

        <p style="font-size:13px;color:#666;">
            Si tenés consultas, comunicate directamente con el negocio.
        </p>

        <hr style="border:none;border-top:1px solid #eee;margin:24px 0;" />
        <p style="font-size:12px;color:#aaa;text-align:center;">
            Reservado a través de TurnoGo
        </p>
    </div>
    """

    params = {
        "from": FROM_ADDRESS,
        "to": [email],
        "subject": f"Turno confirmado en {nombre_negocio}",
        "html": html,
        "attachments": [
            {
                "filename": "qr_turno.png",
                "content": list(qr_bytes),
                "content_type": "image/png",
                "content_id": "qr_turno",
            }
        ],
    }

    return resend.Emails.send(params)


def send_two_factor_email(
    email: str,
    code: str,
):
    """
    Envía el código OTP para el segundo factor de autenticación.
    """

    params = {
        "from": FROM_ADDRESS,
        "to": [email],
        "subject": "Código de verificación - TurnoGo",
        "html": f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:32px;background:#ffffff;">

            <h2 style="color:#1f2937;text-align:center;">
                Verificación en dos pasos
            </h2>

            <p style="font-size:16px;color:#4b5563;">
                Detectamos un intento de inicio de sesión en tu cuenta de
                <strong>TurnoGo</strong>.
            </p>

            <p style="font-size:16px;color:#4b5563;">
                Para continuar ingresá el siguiente código:
            </p>

            <div
                style="
                    margin:32px auto;
                    width:220px;
                    padding:18px;
                    background:#f3f4f6;
                    border-radius:12px;
                    text-align:center;
                    font-size:34px;
                    font-weight:bold;
                    letter-spacing:8px;
                    color:#111827;
                "
            >
                {code}
            </div>

            <p style="font-size:15px;color:#6b7280;">
                Este código vencerá en
                <strong>10 minutos</strong>.
            </p>

            <p style="font-size:15px;color:#6b7280;">
                Si no intentaste iniciar sesión,
                simplemente ignorá este correo.
            </p>

            <hr style="margin:30px 0;">

            <p style="font-size:12px;color:#9ca3af;text-align:center;">
                © TurnoGo
            </p>

        </div>
        """,
    }

    try:
        response = resend.Emails.send(params)

        print("=== OTP ENVIADO ===")
        print(response)

        return response

    except Exception as e:
        print("=== ERROR ENVIANDO OTP ===")
        print(e)
        raise


def send_account_linked_email(email: str,):
    """Envía un correo notificando que la cuenta fue vinculada con Google."""
    params = {
        "from": FROM_ADDRESS,
        "to": [email],
        "subject": "Vinculaste tu cuenta con Google",
        "html": """
        <div style="font-family: Arial, sans-serif; max-width:600px; margin:auto;">
            <h2>Cuenta vinculada con Google</h2>

            <p>
                Tu cuenta de TurnoGo ahora está vinculada con tu cuenta
                de Google.
            </p>

            <p>
                A partir de ahora podés iniciar sesión con tu email y
                contraseña, o directamente con Google. Tus datos y turnos
                son los mismos en ambos métodos.
            </p>

            <hr>

            <p style="font-size:12px;color:#888;">
                Si no fuiste vos quien inició sesión con Google,
                comunicate con el equipo de TurnoGo.
            </p>
        </div>
        """,
    }

    return resend.Emails.send(params)


def send_otp_email(email: str, code: str):
    params = {
        "from": FROM_ADDRESS,
        "to": [email],
        "subject": "Código de verificación de TurnoGo",
        "html": f"""
        <div style="font-family: Arial, sans-serif; max-width:600px; margin:auto;">
            <h2>Verificación en dos pasos</h2>

            <p>Utilizá el siguiente código para completar el inicio de sesión:</p>

            <div style="
                font-size:36px;
                font-weight:bold;
                text-align:center;
                letter-spacing:8px;
                margin:30px 0;
                color:#b45309;
            ">
                {code}
            </div>

            <p>
                Este código tiene una validez de
                <strong>10 minutos</strong>.
            </p>

            <p>
                Si no intentaste iniciar sesión,
                simplemente ignorá este correo.
            </p>

            <hr>

            <p style="font-size:12px;color:#888;">
                Equipo de TurnoGo
            </p>
        </div>
        """,
    }

    return resend.Emails.send(params)


def send_calendario_email(
    email: str,
    link: str,
    nombre_empleado: str,
):
    """Envía el link del feed de calendario (.ics) a un empleado."""
    params = {
        "from": FROM_ADDRESS,
        "to": [email],
        "subject": "Tu calendario de turnos en TurnoGo",
        "html": f"""
        <div style="font-family: Arial, sans-serif; max-width:600px; margin:auto;">
            <h2>Tu calendario de turnos</h2>

            <p>
                Hola {nombre_empleado}, ya podés agregar tus turnos
                a Google Calendar (u otro cliente compatible con
                calendarios por suscripción).
            </p>

            <p>Copiá este link:</p>

            <p style="
                background:#f3f4f6;
                border-radius:8px;
                padding:12px 16px;
                word-break:break-all;
                font-size:14px;
                color:#111827;
            ">
                {link}
            </p>

            <p>Para agregarlo en Google Calendar:</p>

            <ol style="color:#4b5563;font-size:15px;">
                <li>Abrí Google Calendar</li>
                <li>Andá a "Otros calendarios" y hacé click en "+"</li>
                <li>Elegí "Desde URL"</li>
                <li>Pegá el link de arriba</li>
            </ol>

            <p>
                Va a aparecer un calendario nuevo llamado
                <strong>TurnoGo - {nombre_empleado}</strong>,
                separado de tus eventos personales.
            </p>

            <p style="font-size:13px;color:#666;">
                Nota: Google Calendar actualiza los calendarios externos
                de forma periódica, no al instante. Un turno nuevo puede
                tardar algunas horas en aparecer.
            </p>

            <hr>

            <p style="font-size:12px;color:#888;">
                Equipo de TurnoGo
            </p>
        </div>
        """,
    }

    return resend.Emails.send(params)


def send_cancellation_email(
    email: str,
    id_turno: int,
    nombre_negocio: str,
    nombre_servicio: str,
    fecha: str,
    hora: str,
    motivo: str,
):
    """Envía un correo notificando al cliente la cancelación de su turno."""
    params = {
        "from": FROM_ADDRESS,
        "to": [email],
        "subject": "Tu turno fue cancelado - TurnoGo",
        "html": f"""
        <div style="font-family: Arial, sans-serif; max-width:600px; margin:auto;">
            <h2>Turno cancelado</h2>

            <p>
                Hola, te informamos que tu turno fue cancelado.
            </p>

            <div style="
                background:#f3f4f6;
                border-radius:8px;
                padding:16px;
                margin:20px 0;
            ">
                <p>
                    <strong>Negocio:</strong> {nombre_negocio}
                </p>
                <p>
                    <strong>Servicio:</strong> {nombre_servicio}
                </p>
                <p>
                    <strong>Fecha:</strong> {fecha}
                </p>
                <p>
                    <strong>Hora:</strong> {hora}
                </p>
                <p>
                    <strong>Turno:</strong> #{id_turno}
                </p>
            </div>

            <p>
                <strong>Motivo de la cancelación:</strong>
            </p>

            <p>
                {motivo}
            </p>

            <p>
                Si necesitás reservar un nuevo turno, podés hacerlo
                nuevamente desde TurnoGo.
            </p>

            <hr>

            <p style="font-size:12px;color:#888;">
                Equipo de TurnoGo
            </p>
        </div>
        """,
    }

    return resend.Emails.send(params)