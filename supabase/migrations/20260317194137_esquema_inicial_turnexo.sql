drop extension if exists "pg_net";

create extension if not exists "btree_gist" with schema "public";

create sequence "public"."admin_id_admin_seq";

create sequence "public"."cliente_id_cliente_seq";

create sequence "public"."empleado_id_empleado_seq";

create sequence "public"."estado_turno_id_estado_seq";

create sequence "public"."localidades_id_localidad_seq";

create sequence "public"."mensaje_whatsapp_id_mensaje_seq";

create sequence "public"."negocios_id_negocio_seq";

create sequence "public"."provincias_id_provincia_seq";

create sequence "public"."servicio_id_servicio_seq";

create sequence "public"."turno_id_turno_seq";

create sequence "public"."usuarios_id_us_seq";


  create table "public"."admin" (
    "id_admin" bigint not null default nextval('public.admin_id_admin_seq'::regclass),
    "usuario" character varying(80) not null,
    "password_hash" text not null,
    "created_at" timestamp with time zone not null default now()
      );



  create table "public"."cierre_mensual" (
    "año" integer not null,
    "mes" integer not null,
    "total_facturado" numeric(12,2) not null,
    "cant_turnos" integer not null,
    "cantidad_clientes_unicos" integer not null,
    "created_at" timestamp with time zone not null default now()
      );



  create table "public"."cliente" (
    "id_cliente" bigint not null default nextval('public.cliente_id_cliente_seq'::regclass),
    "telefono" character varying(30) not null,
    "nombre" character varying(80) not null,
    "apellido" character varying(80) not null,
    "created_at" timestamp with time zone not null default now()
      );



  create table "public"."empleado" (
    "id_empleado" bigint not null default nextval('public.empleado_id_empleado_seq'::regclass),
    "nombre" character varying(80) not null,
    "apellido" character varying(80) not null,
    "telefono" character varying(30),
    "activo" boolean not null default true
      );



  create table "public"."estado_turno" (
    "id_estado" smallint not null default nextval('public.estado_turno_id_estado_seq'::regclass),
    "nombre_estado" character varying(60) not null
      );



  create table "public"."localidades" (
    "id_localidad" integer not null default nextval('public.localidades_id_localidad_seq'::regclass),
    "nombre" character varying(150) not null,
    "id_provincia" integer not null
      );



  create table "public"."mensaje_whatsapp" (
    "id_mensaje" bigint not null default nextval('public.mensaje_whatsapp_id_mensaje_seq'::regclass),
    "id_turno" bigint not null,
    "tipo" character varying(40) not null,
    "contenido" text not null,
    "estado_envio" character varying(20) not null,
    "enviado_at" timestamp with time zone
      );



  create table "public"."negocios" (
    "id_negocio" integer not null default nextval('public.negocios_id_negocio_seq'::regclass),
    "nombre" character varying(150) not null,
    "rubro" character varying(100) not null,
    "wsp" character varying(20),
    "telefono" character varying(20),
    "direccion" character varying(200),
    "ciudad" character varying(100),
    "id_localidad" integer,
    "id_provincia" integer,
    "ig_url" character varying(200),
    "url_fb" character varying(200),
    "logo" character varying(255),
    "activo" boolean default true,
    "creado_at" timestamp without time zone default CURRENT_TIMESTAMP
      );



  create table "public"."provincias" (
    "id_provincia" integer not null default nextval('public.provincias_id_provincia_seq'::regclass),
    "nombre" character varying(100) not null
      );



  create table "public"."servicio" (
    "id_servicio" bigint not null default nextval('public.servicio_id_servicio_seq'::regclass),
    "nombre_servicio" character varying(80) not null,
    "precio" numeric(10,2) not null,
    "requiere_aprobacion" boolean not null default false,
    "duracion_min" integer not null,
    "duracion_max" integer,
    "activo" boolean not null default true
      );



  create table "public"."turno" (
    "id_turno" bigint not null default nextval('public.turno_id_turno_seq'::regclass),
    "id_cliente" bigint not null,
    "id_servicio" bigint not null,
    "id_estado" smallint not null,
    "id_empleado" bigint,
    "id_admin_aprobador" bigint,
    "fecha_hora_inicio" timestamp with time zone not null,
    "fecha_hora_fin" timestamp with time zone not null,
    "aprobado_at" timestamp with time zone,
    "rechazado_motivo" text,
    "created_at" timestamp with time zone not null default now(),
    "updated_at" timestamp with time zone default now(),
    "id_negocio" bigint
      );



  create table "public"."usuarios" (
    "id_us" integer not null default nextval('public.usuarios_id_us_seq'::regclass),
    "usuario_us" character varying(30) not null,
    "email_us" character varying(50) not null,
    "contrasena_us" character varying(50) not null,
    "created_at" timestamp without time zone default CURRENT_TIMESTAMP
      );


alter sequence "public"."admin_id_admin_seq" owned by "public"."admin"."id_admin";

alter sequence "public"."cliente_id_cliente_seq" owned by "public"."cliente"."id_cliente";

alter sequence "public"."empleado_id_empleado_seq" owned by "public"."empleado"."id_empleado";

alter sequence "public"."estado_turno_id_estado_seq" owned by "public"."estado_turno"."id_estado";

alter sequence "public"."localidades_id_localidad_seq" owned by "public"."localidades"."id_localidad";

alter sequence "public"."mensaje_whatsapp_id_mensaje_seq" owned by "public"."mensaje_whatsapp"."id_mensaje";

alter sequence "public"."negocios_id_negocio_seq" owned by "public"."negocios"."id_negocio";

alter sequence "public"."provincias_id_provincia_seq" owned by "public"."provincias"."id_provincia";

alter sequence "public"."servicio_id_servicio_seq" owned by "public"."servicio"."id_servicio";

alter sequence "public"."turno_id_turno_seq" owned by "public"."turno"."id_turno";

alter sequence "public"."usuarios_id_us_seq" owned by "public"."usuarios"."id_us";

CREATE UNIQUE INDEX admin_pkey ON public.admin USING btree (id_admin);

CREATE UNIQUE INDEX admin_usuario_key ON public.admin USING btree (usuario);

CREATE UNIQUE INDEX cliente_pkey ON public.cliente USING btree (id_cliente);

CREATE UNIQUE INDEX cliente_telefono_key ON public.cliente USING btree (telefono);

CREATE UNIQUE INDEX empleado_pkey ON public.empleado USING btree (id_empleado);

CREATE UNIQUE INDEX empleado_telefono_key ON public.empleado USING btree (telefono);

CREATE UNIQUE INDEX estado_turno_nombre_estado_key ON public.estado_turno USING btree (nombre_estado);

CREATE UNIQUE INDEX estado_turno_pkey ON public.estado_turno USING btree (id_estado);

select 1; 
-- CREATE INDEX ex_turno_no_solapa_por_empleado ON public.turno USING gist (id_empleado, tstzrange(fecha_hora_inicio, fecha_hora_fin, '[)'::text));

CREATE UNIQUE INDEX localidades_pkey ON public.localidades USING btree (id_localidad);

CREATE UNIQUE INDEX mensaje_whatsapp_pkey ON public.mensaje_whatsapp USING btree (id_mensaje);

CREATE UNIQUE INDEX negocios_pkey ON public.negocios USING btree (id_negocio);

CREATE UNIQUE INDEX pk_cierre_mensual ON public.cierre_mensual USING btree ("año", mes);

CREATE UNIQUE INDEX provincias_nombre_key ON public.provincias USING btree (nombre);

CREATE UNIQUE INDEX provincias_pkey ON public.provincias USING btree (id_provincia);

CREATE UNIQUE INDEX servicio_nombre_servicio_key ON public.servicio USING btree (nombre_servicio);

CREATE UNIQUE INDEX servicio_pkey ON public.servicio USING btree (id_servicio);

CREATE UNIQUE INDEX turno_pkey ON public.turno USING btree (id_turno);

CREATE UNIQUE INDEX usuarios_email_us_key ON public.usuarios USING btree (email_us);

CREATE UNIQUE INDEX usuarios_pkey ON public.usuarios USING btree (id_us);

CREATE UNIQUE INDEX usuarios_usuario_us_key ON public.usuarios USING btree (usuario_us);

alter table "public"."admin" add constraint "admin_pkey" PRIMARY KEY using index "admin_pkey";

alter table "public"."cierre_mensual" add constraint "pk_cierre_mensual" PRIMARY KEY using index "pk_cierre_mensual";

alter table "public"."cliente" add constraint "cliente_pkey" PRIMARY KEY using index "cliente_pkey";

alter table "public"."empleado" add constraint "empleado_pkey" PRIMARY KEY using index "empleado_pkey";

alter table "public"."estado_turno" add constraint "estado_turno_pkey" PRIMARY KEY using index "estado_turno_pkey";

alter table "public"."localidades" add constraint "localidades_pkey" PRIMARY KEY using index "localidades_pkey";

alter table "public"."mensaje_whatsapp" add constraint "mensaje_whatsapp_pkey" PRIMARY KEY using index "mensaje_whatsapp_pkey";

alter table "public"."negocios" add constraint "negocios_pkey" PRIMARY KEY using index "negocios_pkey";

alter table "public"."provincias" add constraint "provincias_pkey" PRIMARY KEY using index "provincias_pkey";

alter table "public"."servicio" add constraint "servicio_pkey" PRIMARY KEY using index "servicio_pkey";

alter table "public"."turno" add constraint "turno_pkey" PRIMARY KEY using index "turno_pkey";

alter table "public"."usuarios" add constraint "usuarios_pkey" PRIMARY KEY using index "usuarios_pkey";

alter table "public"."admin" add constraint "admin_usuario_key" UNIQUE using index "admin_usuario_key";

alter table "public"."cierre_mensual" add constraint "chk_cierre_año" CHECK (("año" >= 2000)) not valid;

alter table "public"."cierre_mensual" validate constraint "chk_cierre_año";

alter table "public"."cierre_mensual" add constraint "chk_cierre_mes" CHECK (((mes >= 1) AND (mes <= 12))) not valid;

alter table "public"."cierre_mensual" validate constraint "chk_cierre_mes";

alter table "public"."cierre_mensual" add constraint "cierre_mensual_cant_turnos_check" CHECK ((cant_turnos >= 0)) not valid;

alter table "public"."cierre_mensual" validate constraint "cierre_mensual_cant_turnos_check";

alter table "public"."cierre_mensual" add constraint "cierre_mensual_cantidad_clientes_unicos_check" CHECK ((cantidad_clientes_unicos >= 0)) not valid;

alter table "public"."cierre_mensual" validate constraint "cierre_mensual_cantidad_clientes_unicos_check";

alter table "public"."cierre_mensual" add constraint "cierre_mensual_total_facturado_check" CHECK ((total_facturado >= (0)::numeric)) not valid;

alter table "public"."cierre_mensual" validate constraint "cierre_mensual_total_facturado_check";

alter table "public"."cliente" add constraint "chk_cliente_telefono_len" CHECK ((length((telefono)::text) >= 8)) not valid;

alter table "public"."cliente" validate constraint "chk_cliente_telefono_len";

alter table "public"."cliente" add constraint "cliente_telefono_key" UNIQUE using index "cliente_telefono_key";

alter table "public"."empleado" add constraint "empleado_telefono_key" UNIQUE using index "empleado_telefono_key";

alter table "public"."estado_turno" add constraint "estado_turno_nombre_estado_key" UNIQUE using index "estado_turno_nombre_estado_key";

alter table "public"."localidades" add constraint "fk_localidad_provincia" FOREIGN KEY (id_provincia) REFERENCES public.provincias(id_provincia) not valid;

alter table "public"."localidades" validate constraint "fk_localidad_provincia";

alter table "public"."mensaje_whatsapp" add constraint "chk_mensaje_estado_envio" CHECK (((estado_envio)::text = ANY ((ARRAY['pendiente'::character varying, 'enviado'::character varying, 'error'::character varying])::text[]))) not valid;

alter table "public"."mensaje_whatsapp" validate constraint "chk_mensaje_estado_envio";

alter table "public"."mensaje_whatsapp" add constraint "chk_mensaje_tipo" CHECK (((tipo)::text = ANY ((ARRAY['confirmacion'::character varying, 'pago'::character varying, 'cancelacion'::character varying, 'reprogramacion'::character varying, 'oferta_adelanto'::character varying])::text[]))) not valid;

alter table "public"."mensaje_whatsapp" validate constraint "chk_mensaje_tipo";

alter table "public"."mensaje_whatsapp" add constraint "mensaje_whatsapp_id_turno_fkey" FOREIGN KEY (id_turno) REFERENCES public.turno(id_turno) not valid;

alter table "public"."mensaje_whatsapp" validate constraint "mensaje_whatsapp_id_turno_fkey";

alter table "public"."negocios" add constraint "fk_negocio_localidad" FOREIGN KEY (id_localidad) REFERENCES public.localidades(id_localidad) not valid;

alter table "public"."negocios" validate constraint "fk_negocio_localidad";

alter table "public"."negocios" add constraint "fk_negocio_provincia" FOREIGN KEY (id_provincia) REFERENCES public.provincias(id_provincia) not valid;

alter table "public"."negocios" validate constraint "fk_negocio_provincia";

alter table "public"."provincias" add constraint "provincias_nombre_key" UNIQUE using index "provincias_nombre_key";

alter table "public"."servicio" add constraint "chk_servicio_duracionmax" CHECK (((duracion_max IS NULL) OR (duracion_max >= duracion_min))) not valid;

alter table "public"."servicio" validate constraint "chk_servicio_duracionmax";

alter table "public"."servicio" add constraint "servicio_duracion_min_check" CHECK ((duracion_min > 0)) not valid;

alter table "public"."servicio" validate constraint "servicio_duracion_min_check";

alter table "public"."servicio" add constraint "servicio_nombre_servicio_key" UNIQUE using index "servicio_nombre_servicio_key";

alter table "public"."servicio" add constraint "servicio_precio_check" CHECK ((precio >= (0)::numeric)) not valid;

alter table "public"."servicio" validate constraint "servicio_precio_check";

alter table "public"."turno" add constraint "chk_turno_rango" CHECK ((fecha_hora_fin > fecha_hora_inicio)) not valid;

alter table "public"."turno" validate constraint "chk_turno_rango";

alter table "public"."turno" add constraint "ex_turno_no_solapa_por_empleado" EXCLUDE USING gist (id_empleado WITH =, tstzrange(fecha_hora_inicio, fecha_hora_fin, '[)'::text) WITH &&);

alter table "public"."turno" add constraint "fk_turno_negocio" FOREIGN KEY (id_negocio) REFERENCES public.negocios(id_negocio) not valid;

alter table "public"."turno" validate constraint "fk_turno_negocio";

alter table "public"."turno" add constraint "turno_id_admin_aprobador_fkey" FOREIGN KEY (id_admin_aprobador) REFERENCES public.admin(id_admin) not valid;

alter table "public"."turno" validate constraint "turno_id_admin_aprobador_fkey";

alter table "public"."turno" add constraint "turno_id_cliente_fkey" FOREIGN KEY (id_cliente) REFERENCES public.cliente(id_cliente) not valid;

alter table "public"."turno" validate constraint "turno_id_cliente_fkey";

alter table "public"."turno" add constraint "turno_id_empleado_fkey" FOREIGN KEY (id_empleado) REFERENCES public.empleado(id_empleado) not valid;

alter table "public"."turno" validate constraint "turno_id_empleado_fkey";

alter table "public"."turno" add constraint "turno_id_estado_fkey" FOREIGN KEY (id_estado) REFERENCES public.estado_turno(id_estado) not valid;

alter table "public"."turno" validate constraint "turno_id_estado_fkey";

alter table "public"."turno" add constraint "turno_id_servicio_fkey" FOREIGN KEY (id_servicio) REFERENCES public.servicio(id_servicio) not valid;

alter table "public"."turno" validate constraint "turno_id_servicio_fkey";

alter table "public"."usuarios" add constraint "usuarios_email_us_key" UNIQUE using index "usuarios_email_us_key";

alter table "public"."usuarios" add constraint "usuarios_usuario_us_key" UNIQUE using index "usuarios_usuario_us_key";

grant delete on table "public"."admin" to "anon";

grant insert on table "public"."admin" to "anon";

grant references on table "public"."admin" to "anon";

grant select on table "public"."admin" to "anon";

grant trigger on table "public"."admin" to "anon";

grant truncate on table "public"."admin" to "anon";

grant update on table "public"."admin" to "anon";

grant delete on table "public"."admin" to "authenticated";

grant insert on table "public"."admin" to "authenticated";

grant references on table "public"."admin" to "authenticated";

grant select on table "public"."admin" to "authenticated";

grant trigger on table "public"."admin" to "authenticated";

grant truncate on table "public"."admin" to "authenticated";

grant update on table "public"."admin" to "authenticated";

grant delete on table "public"."admin" to "service_role";

grant insert on table "public"."admin" to "service_role";

grant references on table "public"."admin" to "service_role";

grant select on table "public"."admin" to "service_role";

grant trigger on table "public"."admin" to "service_role";

grant truncate on table "public"."admin" to "service_role";

grant update on table "public"."admin" to "service_role";

grant delete on table "public"."cierre_mensual" to "anon";

grant insert on table "public"."cierre_mensual" to "anon";

grant references on table "public"."cierre_mensual" to "anon";

grant select on table "public"."cierre_mensual" to "anon";

grant trigger on table "public"."cierre_mensual" to "anon";

grant truncate on table "public"."cierre_mensual" to "anon";

grant update on table "public"."cierre_mensual" to "anon";

grant delete on table "public"."cierre_mensual" to "authenticated";

grant insert on table "public"."cierre_mensual" to "authenticated";

grant references on table "public"."cierre_mensual" to "authenticated";

grant select on table "public"."cierre_mensual" to "authenticated";

grant trigger on table "public"."cierre_mensual" to "authenticated";

grant truncate on table "public"."cierre_mensual" to "authenticated";

grant update on table "public"."cierre_mensual" to "authenticated";

grant delete on table "public"."cierre_mensual" to "service_role";

grant insert on table "public"."cierre_mensual" to "service_role";

grant references on table "public"."cierre_mensual" to "service_role";

grant select on table "public"."cierre_mensual" to "service_role";

grant trigger on table "public"."cierre_mensual" to "service_role";

grant truncate on table "public"."cierre_mensual" to "service_role";

grant update on table "public"."cierre_mensual" to "service_role";

grant delete on table "public"."cliente" to "anon";

grant insert on table "public"."cliente" to "anon";

grant references on table "public"."cliente" to "anon";

grant select on table "public"."cliente" to "anon";

grant trigger on table "public"."cliente" to "anon";

grant truncate on table "public"."cliente" to "anon";

grant update on table "public"."cliente" to "anon";

grant delete on table "public"."cliente" to "authenticated";

grant insert on table "public"."cliente" to "authenticated";

grant references on table "public"."cliente" to "authenticated";

grant select on table "public"."cliente" to "authenticated";

grant trigger on table "public"."cliente" to "authenticated";

grant truncate on table "public"."cliente" to "authenticated";

grant update on table "public"."cliente" to "authenticated";

grant delete on table "public"."cliente" to "service_role";

grant insert on table "public"."cliente" to "service_role";

grant references on table "public"."cliente" to "service_role";

grant select on table "public"."cliente" to "service_role";

grant trigger on table "public"."cliente" to "service_role";

grant truncate on table "public"."cliente" to "service_role";

grant update on table "public"."cliente" to "service_role";

grant delete on table "public"."empleado" to "anon";

grant insert on table "public"."empleado" to "anon";

grant references on table "public"."empleado" to "anon";

grant select on table "public"."empleado" to "anon";

grant trigger on table "public"."empleado" to "anon";

grant truncate on table "public"."empleado" to "anon";

grant update on table "public"."empleado" to "anon";

grant delete on table "public"."empleado" to "authenticated";

grant insert on table "public"."empleado" to "authenticated";

grant references on table "public"."empleado" to "authenticated";

grant select on table "public"."empleado" to "authenticated";

grant trigger on table "public"."empleado" to "authenticated";

grant truncate on table "public"."empleado" to "authenticated";

grant update on table "public"."empleado" to "authenticated";

grant delete on table "public"."empleado" to "service_role";

grant insert on table "public"."empleado" to "service_role";

grant references on table "public"."empleado" to "service_role";

grant select on table "public"."empleado" to "service_role";

grant trigger on table "public"."empleado" to "service_role";

grant truncate on table "public"."empleado" to "service_role";

grant update on table "public"."empleado" to "service_role";

grant delete on table "public"."estado_turno" to "anon";

grant insert on table "public"."estado_turno" to "anon";

grant references on table "public"."estado_turno" to "anon";

grant select on table "public"."estado_turno" to "anon";

grant trigger on table "public"."estado_turno" to "anon";

grant truncate on table "public"."estado_turno" to "anon";

grant update on table "public"."estado_turno" to "anon";

grant delete on table "public"."estado_turno" to "authenticated";

grant insert on table "public"."estado_turno" to "authenticated";

grant references on table "public"."estado_turno" to "authenticated";

grant select on table "public"."estado_turno" to "authenticated";

grant trigger on table "public"."estado_turno" to "authenticated";

grant truncate on table "public"."estado_turno" to "authenticated";

grant update on table "public"."estado_turno" to "authenticated";

grant delete on table "public"."estado_turno" to "service_role";

grant insert on table "public"."estado_turno" to "service_role";

grant references on table "public"."estado_turno" to "service_role";

grant select on table "public"."estado_turno" to "service_role";

grant trigger on table "public"."estado_turno" to "service_role";

grant truncate on table "public"."estado_turno" to "service_role";

grant update on table "public"."estado_turno" to "service_role";

grant delete on table "public"."localidades" to "anon";

grant insert on table "public"."localidades" to "anon";

grant references on table "public"."localidades" to "anon";

grant select on table "public"."localidades" to "anon";

grant trigger on table "public"."localidades" to "anon";

grant truncate on table "public"."localidades" to "anon";

grant update on table "public"."localidades" to "anon";

grant delete on table "public"."localidades" to "authenticated";

grant insert on table "public"."localidades" to "authenticated";

grant references on table "public"."localidades" to "authenticated";

grant select on table "public"."localidades" to "authenticated";

grant trigger on table "public"."localidades" to "authenticated";

grant truncate on table "public"."localidades" to "authenticated";

grant update on table "public"."localidades" to "authenticated";

grant delete on table "public"."localidades" to "service_role";

grant insert on table "public"."localidades" to "service_role";

grant references on table "public"."localidades" to "service_role";

grant select on table "public"."localidades" to "service_role";

grant trigger on table "public"."localidades" to "service_role";

grant truncate on table "public"."localidades" to "service_role";

grant update on table "public"."localidades" to "service_role";

grant delete on table "public"."mensaje_whatsapp" to "anon";

grant insert on table "public"."mensaje_whatsapp" to "anon";

grant references on table "public"."mensaje_whatsapp" to "anon";

grant select on table "public"."mensaje_whatsapp" to "anon";

grant trigger on table "public"."mensaje_whatsapp" to "anon";

grant truncate on table "public"."mensaje_whatsapp" to "anon";

grant update on table "public"."mensaje_whatsapp" to "anon";

grant delete on table "public"."mensaje_whatsapp" to "authenticated";

grant insert on table "public"."mensaje_whatsapp" to "authenticated";

grant references on table "public"."mensaje_whatsapp" to "authenticated";

grant select on table "public"."mensaje_whatsapp" to "authenticated";

grant trigger on table "public"."mensaje_whatsapp" to "authenticated";

grant truncate on table "public"."mensaje_whatsapp" to "authenticated";

grant update on table "public"."mensaje_whatsapp" to "authenticated";

grant delete on table "public"."mensaje_whatsapp" to "service_role";

grant insert on table "public"."mensaje_whatsapp" to "service_role";

grant references on table "public"."mensaje_whatsapp" to "service_role";

grant select on table "public"."mensaje_whatsapp" to "service_role";

grant trigger on table "public"."mensaje_whatsapp" to "service_role";

grant truncate on table "public"."mensaje_whatsapp" to "service_role";

grant update on table "public"."mensaje_whatsapp" to "service_role";

grant delete on table "public"."negocios" to "anon";

grant insert on table "public"."negocios" to "anon";

grant references on table "public"."negocios" to "anon";

grant select on table "public"."negocios" to "anon";

grant trigger on table "public"."negocios" to "anon";

grant truncate on table "public"."negocios" to "anon";

grant update on table "public"."negocios" to "anon";

grant delete on table "public"."negocios" to "authenticated";

grant insert on table "public"."negocios" to "authenticated";

grant references on table "public"."negocios" to "authenticated";

grant select on table "public"."negocios" to "authenticated";

grant trigger on table "public"."negocios" to "authenticated";

grant truncate on table "public"."negocios" to "authenticated";

grant update on table "public"."negocios" to "authenticated";

grant delete on table "public"."negocios" to "service_role";

grant insert on table "public"."negocios" to "service_role";

grant references on table "public"."negocios" to "service_role";

grant select on table "public"."negocios" to "service_role";

grant trigger on table "public"."negocios" to "service_role";

grant truncate on table "public"."negocios" to "service_role";

grant update on table "public"."negocios" to "service_role";

grant delete on table "public"."provincias" to "anon";

grant insert on table "public"."provincias" to "anon";

grant references on table "public"."provincias" to "anon";

grant select on table "public"."provincias" to "anon";

grant trigger on table "public"."provincias" to "anon";

grant truncate on table "public"."provincias" to "anon";

grant update on table "public"."provincias" to "anon";

grant delete on table "public"."provincias" to "authenticated";

grant insert on table "public"."provincias" to "authenticated";

grant references on table "public"."provincias" to "authenticated";

grant select on table "public"."provincias" to "authenticated";

grant trigger on table "public"."provincias" to "authenticated";

grant truncate on table "public"."provincias" to "authenticated";

grant update on table "public"."provincias" to "authenticated";

grant delete on table "public"."provincias" to "service_role";

grant insert on table "public"."provincias" to "service_role";

grant references on table "public"."provincias" to "service_role";

grant select on table "public"."provincias" to "service_role";

grant trigger on table "public"."provincias" to "service_role";

grant truncate on table "public"."provincias" to "service_role";

grant update on table "public"."provincias" to "service_role";

grant delete on table "public"."servicio" to "anon";

grant insert on table "public"."servicio" to "anon";

grant references on table "public"."servicio" to "anon";

grant select on table "public"."servicio" to "anon";

grant trigger on table "public"."servicio" to "anon";

grant truncate on table "public"."servicio" to "anon";

grant update on table "public"."servicio" to "anon";

grant delete on table "public"."servicio" to "authenticated";

grant insert on table "public"."servicio" to "authenticated";

grant references on table "public"."servicio" to "authenticated";

grant select on table "public"."servicio" to "authenticated";

grant trigger on table "public"."servicio" to "authenticated";

grant truncate on table "public"."servicio" to "authenticated";

grant update on table "public"."servicio" to "authenticated";

grant delete on table "public"."servicio" to "service_role";

grant insert on table "public"."servicio" to "service_role";

grant references on table "public"."servicio" to "service_role";

grant select on table "public"."servicio" to "service_role";

grant trigger on table "public"."servicio" to "service_role";

grant truncate on table "public"."servicio" to "service_role";

grant update on table "public"."servicio" to "service_role";

grant delete on table "public"."turno" to "anon";

grant insert on table "public"."turno" to "anon";

grant references on table "public"."turno" to "anon";

grant select on table "public"."turno" to "anon";

grant trigger on table "public"."turno" to "anon";

grant truncate on table "public"."turno" to "anon";

grant update on table "public"."turno" to "anon";

grant delete on table "public"."turno" to "authenticated";

grant insert on table "public"."turno" to "authenticated";

grant references on table "public"."turno" to "authenticated";

grant select on table "public"."turno" to "authenticated";

grant trigger on table "public"."turno" to "authenticated";

grant truncate on table "public"."turno" to "authenticated";

grant update on table "public"."turno" to "authenticated";

grant delete on table "public"."turno" to "service_role";

grant insert on table "public"."turno" to "service_role";

grant references on table "public"."turno" to "service_role";

grant select on table "public"."turno" to "service_role";

grant trigger on table "public"."turno" to "service_role";

grant truncate on table "public"."turno" to "service_role";

grant update on table "public"."turno" to "service_role";

grant delete on table "public"."usuarios" to "anon";

grant insert on table "public"."usuarios" to "anon";

grant references on table "public"."usuarios" to "anon";

grant select on table "public"."usuarios" to "anon";

grant trigger on table "public"."usuarios" to "anon";

grant truncate on table "public"."usuarios" to "anon";

grant update on table "public"."usuarios" to "anon";

grant delete on table "public"."usuarios" to "authenticated";

grant insert on table "public"."usuarios" to "authenticated";

grant references on table "public"."usuarios" to "authenticated";

grant select on table "public"."usuarios" to "authenticated";

grant trigger on table "public"."usuarios" to "authenticated";

grant truncate on table "public"."usuarios" to "authenticated";

grant update on table "public"."usuarios" to "authenticated";

grant delete on table "public"."usuarios" to "service_role";

grant insert on table "public"."usuarios" to "service_role";

grant references on table "public"."usuarios" to "service_role";

grant select on table "public"."usuarios" to "service_role";

grant trigger on table "public"."usuarios" to "service_role";

grant truncate on table "public"."usuarios" to "service_role";

grant update on table "public"."usuarios" to "service_role";


