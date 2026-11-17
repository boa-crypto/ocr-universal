"""CSV groupé : valeur retenue explicite et neutralisation existante étendue."""
import csv
from io import StringIO

import pytest
from test_field_correction_scope import auth, fingerprint, perform
from test_field_correction_scope import scoped as scoped

from unocr import api

KEYS=("confirmed_value","corrected_value","normalized_value","raw_value")
PREFIX=["document","champ","valeur_brute","valeur_normalisee","confiance","statut"]
HEADER=PREFIX+["valeur_retenue","origine_valeur"]


def seed(scoped,**values):
    job=scoped[1]["visible"]
    result=api.store.load_result(job)
    field=result["fields"]["sample"]
    field.update({k:None for k in KEYS})
    field.update(values)
    api.store.save_result(job,result)
    return job


def download(scoped,who="a",kind="visible",ids=None):
    client,jobs,_=scoped
    return client.get("/api/batches/export/csv",headers=auth(who),params={"ids":ids or jobs[kind]})


def rows(response):
    assert response.status_code==200,response.text
    assert response.content.startswith(b'\xef\xbb\xbf')
    reader=csv.DictReader(StringIO(response.content.decode("utf-8-sig")))
    return reader.fieldnames,list(reader)


@pytest.mark.parametrize("index",range(4))
def test_first_non_none_value_is_exported_without_changing_other_columns(scoped,index):
    values={k:None if i<index else f"VALUE92-{i}" for i,k in enumerate(KEYS)}
    job=seed(scoped,**values,value_origin="DECLARED92")
    before=fingerprint(job)
    header,records=rows(download(scoped))
    assert header==HEADER and len(records)==1
    row=records[0]
    assert row["valeur_retenue"]==f"VALUE92-{index}"
    assert row["origine_valeur"]=="DECLARED92"
    assert row["valeur_brute"]==str(values["raw_value"])
    assert row["valeur_normalisee"]==("" if values["normalized_value"] is None else values["normalized_value"])
    assert fingerprint(job)==before


@pytest.mark.parametrize("index",range(4))
def test_empty_value_is_not_replaced_by_lower_priority_value(scoped,index):
    values={k:None if i<index else ("" if i==index else "LOWER92") for i,k in enumerate(KEYS)}
    seed(scoped,**values)
    assert rows(download(scoped))[1][0]["valeur_retenue"]==""


@pytest.mark.parametrize("slot,value,expected",[("confirmed_value","0","0"),("confirmed_value",0,"0"),
                                              ("confirmed_value",False,"False"),("raw_value",0,"0")])
def test_zero_and_false_legacy_values_are_not_treated_as_absent(scoped,slot,value,expected):
    seed(scoped,**{slot:value})
    assert rows(download(scoped))[1][0]["valeur_retenue"]==expected


def test_all_values_none_exports_empty_retained_value(scoped):
    seed(scoped)
    assert rows(download(scoped))[1][0]["valeur_retenue"]==""


def test_empty_fields_still_exports_header(scoped):
    job=scoped[1]["visible"]
    result=api.store.load_result(job)
    result["fields"]={}
    api.store.save_result(job,result)
    assert rows(download(scoped))==(HEADER,[])


@pytest.mark.parametrize("key,column",[("confidence","confiance"),("status","statut")])
@pytest.mark.parametrize("prefix",["=","+","-","@","\t","\r"])
def test_existing_confidence_and_status_columns_use_csv_neutralizer(scoped,key,column,prefix):
    value=prefix+"VALUE92"
    seed(scoped,**{key:value})
    assert rows(download(scoped))[1][0][column]=="'"+value


@pytest.mark.parametrize("prefix",["=","+","-","@","\t","\r"])
def test_retained_value_uses_csv_neutralizer(scoped,prefix):
    seed(scoped,confirmed_value=prefix+"VALUE92")
    assert rows(download(scoped))[1][0]["valeur_retenue"]=="'"+prefix+"VALUE92"


def test_declared_origin_uses_csv_neutralizer(scoped):
    seed(scoped,value_origin="=ORIGIN92")
    assert rows(download(scoped))[1][0]["origine_valeur"]=="'=ORIGIN92"


@pytest.mark.parametrize("who,kind,status",[("a","hidden",403),("unknown","visible",401),(None,"visible",401)])
def test_access_guard_still_precedes_result_read(scoped,monkeypatch,who,kind,status):
    def forbidden(*args):
        raise AssertionError("lecture avant autorisation")
    monkeypatch.setattr(api.store,"load_result",forbidden)
    assert download(scoped,who,kind).status_code==status


def test_original_six_columns_keep_their_order_and_meaning(scoped):
    seed(scoped,raw_value="RAW92",normalized_value="NORMAL92",confirmed_value="HUMAN92",value_origin="confirmed")
    header,records=rows(download(scoped))
    assert header[:6]==PREFIX and header[6:]==["valeur_retenue","origine_valeur"]
    row=records[0]
    assert [row[k] for k in PREFIX]==["visible.txt","sample","RAW92","NORMAL92","0.4","detected"]
    assert row["valeur_retenue"]=="HUMAN92" and row["origine_valeur"]=="confirmed"


def test_documents_and_duplicate_requests_keep_all_rows(scoped):
    jobs=scoped[1]
    header,records=rows(download(scoped,ids=",".join(jobs[k] for k in ("shared","visible","shared"))))
    assert header==HEADER
    assert [row["document"] for row in records]==["shared.txt","visible.txt","shared.txt"]
    assert all(row["valeur_retenue"]=="NORMAL72" for row in records)


@pytest.mark.parametrize("action,retained,origin",[("confirm","CONFIRMED72","confirmed"),
                                                 ("correct","CORRECTED72","corrected"),("undo","NORMAL72","normalized")])
def test_http_human_changes_appear_in_retained_column(scoped,action,retained,origin):
    client,jobs,_=scoped
    job=jobs["visible"]
    if action=="undo":
        assert perform(client,job,"confirm").status_code==200
    assert perform(client,job,action).status_code==200
    row=rows(download(scoped))[1][0]
    assert row["valeur_retenue"]==retained and row["origine_valeur"]==origin
    assert row["valeur_brute"]=="INITIAL72" and row["valeur_normalisee"]=="NORMAL72"
