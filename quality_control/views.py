from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import UpdateView
from scans.models import Scan
from cradle_of_mankind.decorators import remember_last_query_params
from django.template.defaulttags import register
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from zooniverse.models import Classification, Retirement, Workflow
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


@login_required
@remember_last_query_params('specimen-numbers', ['page'])
def specimen_numbers_list(request):
    workflow = Workflow.objects.get(pk=6400)
    retirement_list = Retirement.objects.filter(
        workflow=workflow).order_by('subject__scan__id')
    page = request.GET.get('page', 1)

    paginator = Paginator(retirement_list, 18)

    try:
        retirements = paginator.page(page)
    except PageNotAnInteger:
        retirements = paginator.page(1)
    except EmptyPage:
        retirements = paginator.page(paginator.num_pages)

    header = ['Pfx', 'AN', 'FN',
              'FN (Pre)', 'Shelf', 'Date', 'Publisher', 'Type', 'PTO']
    values = dict()
    colors = dict()
    for retirement in retirements:
        values[retirement] = len(retirement.classification_set.all())
        colors[retirement] = []
        tasks = ['T9', 'T1', 'T2', 'T5', 'T8', 'T6', 'T3', 'T7', 'T4']
        for task in tasks:
            classifications = retirement.classification_set.all()
            annotations = []
            for classification in classifications:
                annotations.extend(
                    classification.annotation_set.filter(task=task))
            answer_counts = {}
            for annotation in annotations:
                answer_counts[annotation.value] = answer_counts.get(
                    annotation.value, 0) + 1
            similarity_score = max(answer_counts.values()) / len(annotations)
            if similarity_score <= 0.25:
                colors[retirement].append('red')
            elif similarity_score <= 0.5:
                colors[retirement].append('orange')
            elif similarity_score <= 0.75:
                colors[retirement].append('yellow')
            else:
                colors[retirement].append('green')

    return render(request, 'quality_control/quality_control_list.html',
                  {'page_obj': retirements,
                   'header': header,
                   'values': values,
                   'colors': colors})


def specimen_numbers_check(request, pk):
    workflow = Workflow.objects.get(pk=6400)
    scan = Scan.objects.get(id=pk)
    retirement = scan.subject.retirement_set.filter(workflow=workflow).first()
    tasks = {'T9': 'Pfx', 'T1': 'AN', 'T2': 'FN', 'T5': 'FN (Pre)',
             'T8': 'Shelf', 'T6': 'Date', 'T3': 'Publisher',
             'T7': 'Type', 'T4': 'PTO'}
    questions = []
    for task, name in tasks.items():
        classifications = retirement.classification_set.all()
        annotations = []
        for classification in classifications:
            annotations.extend(
                classification.annotation_set.filter(task=task))
        questions.append({name: map(lambda x: x.value, annotations)})

    return render(request, 'quality_control/quality_control_check.html',
                  {'scan': scan, 'questions': questions})


@ register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
