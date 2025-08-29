def test_equipment_flow(client, auth_headers):
    #show form
    res = client.get("/equipment/form", headers=auth_headers)
    assert res.status_code == 200

    #submit equipment
    res = client.post(
        "/equipment/form",
        headers=auth_headers,
        data={
            "cleats": "Nike",
            "cleats_size": "10",
            "helmet": "Riddell",
            "helmet_size": "L",
            "shoudler_pads": "Xenith",
            "pads_size": "M",
            "mouthpiece": "Battle",
            "gloves": "Adidas",
            "contacts": "Yes",
            "measurement": "6ft 200lb",
        }
    )
    assert res.status_code == 303 #redirect to /equipment

    #show equipment room
    res = client.get("/equipment/", headers=auth_headers)
    assert res.status_code == 200
    assert "Nike" in res.text
    