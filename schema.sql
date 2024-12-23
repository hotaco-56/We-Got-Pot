create table
  public.cart_items (
    id bigint generated by default as identity not null,
    created_at timestamp with time zone not null default now(),
    cart_id bigint null,
    sku text null,
    num_ordered integer null default 0,
    completed boolean null default false,
    day text null,
    hour integer null,
    gold integer null default 0,
    constraint cart_items_pkey primary key (id),
    constraint cart_items_cart_id_fkey foreign key (cart_id) references carts (id)
  ) tablespace pg_default;

create table
  public.carts (
    id bigint generated by default as identity not null,
    created_at timestamp with time zone not null default now(),
    customer_name text null default ''::text,
    character_class text null,
    level text null,
    constraint carts_pkey primary key (id)
  ) tablespace pg_default;